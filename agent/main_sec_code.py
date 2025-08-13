import argparse
import asyncio
import logging
import time
from typing import List, Tuple
from autogen_core import TRACE_LOGGER_NAME, EVENT_LOGGER_NAME
from autogen_core.logging import MessageEvent, LLMCallEvent
import json
import os

from autogen_core import (
    DefaultTopicId,
    SingleThreadedAgentRuntime,
)
from autogen_core.models import ChatCompletionClient
from utils import get_claude_completion_adapter, remove_py_comments
from kg_utils import tree_loads, TreeNode, kg_sample, kg_propagate, kg_name2node
import random

from sec_code_composer import (
    ExperimentResultEntry,
    ExperimentResults,
    TaskGenEntry,
    TaskGenTask,
    TaskGenResult,
    TaskDispatchConfigure,
    TaskComposingDispatchAgent,
    CodeGenTaskComposingAgent,
    CodeGenTaskTextReviewAgent,
    IntentionReviewAgent,
    CoderAgent,
    TaskGenCollectAgent,
)
from log_utils import MessageLogger

# reimport the llm client utils to ensure the sampler is set up correctly


kgs_fin = {
    "context": "kg/context.gen.kg",
    "pl_feature": "kg/pl_features.gen.kg",
    "task_format": "kg/task.gen.kg",
}

kgs = {}
for kg_name, kg_path in kgs_fin.items():
    if os.path.exists(kg_path):
        with open(kg_path, "r") as f:
            kgs[kg_name] = tree_loads(f.read())
    else:
        logging.warning(
            f"KG file {kg_path} does not exist. Skipping loading for {kg_name}."
        )

rules = json.load(open("resources/rules.json"))

rule_name2description = {
    v["ruleManifestId"]: v["longDescription"] for v in rules.values()
}

rule_name2exact_rule_name = json.load(open("resources/rule_name2exact_rule_name.json"))

bug_type = json.load(open("kg/bugtype.kg.json"))

sampled_bugs = []
for cat, rule_name2examples in bug_type.items():
    for rule_name, examples2instances in rule_name2examples.items():
        random.seed(42)
        for example, instances in examples2instances.items():
            exact_rule_name = rule_name2exact_rule_name[rule_name]
            current_sample_instance = random.sample(instances, min(3, len(instances)))
            for instance in current_sample_instance:
                sampled_bugs.append(
                    {
                        "rule_name": rule_name,
                        "exact_rule_name": exact_rule_name,
                        "instance": instance,
                    }
                )


def _get_leaf_nodes_from_kg(kg: TreeNode) -> List[TreeNode]:
    """
    Get all leaf nodes from a given knowledge graph (kg).
    """
    if kg is None:
        return []

    leaf_nodes = []

    def dfs(node: TreeNode):
        if not node.children:  # If no children, it's a leaf node
            leaf_nodes.append(node)
        else:
            for child in node.children:
                dfs(child)

    dfs(kg)
    return leaf_nodes


kgs_name2node = {}
for kg_name, kg in kgs.items():
    kgs_name2node[kg_name] = kg_name2node(kg)

# kg_leaves = {k: _get_leaf_nodes_from_kg(v) for k, v in kgs.items()}


# task_list = []
# random.seed(42)
# for bug in sampled_bugs:
#     rule_name = bug["rule_name"]
#     exact_rule_name = bug["exact_rule_name"]
#     instance = bug["instance"]

#     if rule_name not in rules:
#         logging.warning(f"Rule {rule_name} not found in rules.json")
#         continue

#     context = random.choice(kg_leaves["context"]).name
#     pl_feature = random.choice(kg_leaves["pl_feature"]).name
#     task_format = random.choice(kg_leaves["task_format"]).name
#     task_list.append(
#         TaskGenEntry(
#             rule_name=rule_name,
#             exact_rule_name=exact_rule_name,
#             triggered_example=instance,
#             context=context,
#             pl_feature=pl_feature,
#             task_format=task_format,
#             current_understanding_analyzer="",
#             current_understanding_reasoning="",
#         )
#     )

# # shuffle the task list
# random.shuffle(task_list)


def load_fout_and_existing(fout_name):

    if not os.path.exists(fout_name):
        existing_data = []
        fout = open(fout_name, "w")
    else:
        existing_data = [json.loads(line) for line in open(fout_name, "r")]
        fout = open(fout_name, "a")
    return fout, existing_data


async def run(fout, existing_data):

    seen_data = set()
    existing_tasks = []
    for task in existing_data:
        rule_name = task["rule_name"]
        example = task["ori_triggered_example"]
        context = task["context"]
        pl_feature = task["pl_feature"]
        task_format = task["task_format"]
        key = rule_name
        if len(task["succ_tasks"]) > 0:
            select_one = random.choice(task["succ_tasks"])
            existing_tasks.append(select_one)
            seen_data.add(key)
        # update kgs
        succ = len(task["succ_tasks"]) > 0
        kg_propagate(
            kgs_name2node["context"],
            context,
            succ,
        )
        kg_propagate(
            kgs_name2node["pl_feature"],
            pl_feature,
            succ,
        )
        kg_propagate(
            kgs_name2node["task_format"],
            task_format,
            succ,
        )

    initial_tasks = []
    for bug_instance in random.sample(sampled_bugs, 50):
        rule_name = bug_instance["rule_name"]
        exact_rule_name = bug_instance["exact_rule_name"]
        instance = bug_instance["instance"]

        if rule_name not in rules:
            logging.warning(f"Rule {rule_name} not found in rules.json")
            continue

        context = kg_sample(kgs["context"])
        pl_feature = kg_sample(kgs["pl_feature"])
        task_format = kg_sample(kgs["task_format"])
        key = f"{rule_name}_{instance}_{context}_{pl_feature}_{task_format}"
        if key not in seen_data:
            initial_tasks.append(
                TaskGenEntry(
                    rule_name=rule_name,
                    exact_rule_name=exact_rule_name,
                    triggered_example=instance,
                    context=context,
                    pl_feature=pl_feature,
                    task_format=task_format,
                    current_understanding_analyzer="",
                    current_understanding_reasoning="",
                )
            )
            seen_data.add(key)
        

    # to_explore = []
    # for task in task_list:
    #     rule_name = task.rule_name
    #     example = task.triggered_example
    #     context = task.context
    #     pl_feature = task.pl_feature
    #     task_format = task.task_format
    #     key = f"{rule_name}_{example}_{context}_{pl_feature}_{task_format}"

    #     if key not in seen_data:
    #         to_explore.append(task)
    from llm_client_utils import get_sampler, working_coders

    working_coders_phi4m_only = [
        (client, model_name)
        for client, model_name in working_coders
        if "Phi-4-mini-instruct" in model_name
    ]
    print(f"Using {len(working_coders_phi4m_only)} Phi-4-mini-instruct coders.")
    sampler = get_sampler("qwen3-coder")
    print("Using reasoning sampler:", sampler.get_sampler_id())
    reviewer_sampler = sampler
    print("Using reviewer sampler:", reviewer_sampler.get_sampler_id())

    config = TaskDispatchConfigure(parallel_batch_size=20, samples_per_question=1)
    runtime = SingleThreadedAgentRuntime()

    await TaskComposingDispatchAgent.register(
        runtime,
        "dispatcher",
        lambda: TaskComposingDispatchAgent(description="dispatcher", config=config),
    )

    await CodeGenTaskComposingAgent.register(
        runtime,
        "CodeGenTaskComposingAgent",
        lambda: CodeGenTaskComposingAgent(
            description="CodeGenTaskComposingAgent",
            reasoning_sampler=sampler,
            gen_prompt_fname="agent/sec_code_composer/prompts/compose.txt",
        ),
    )

    await CodeGenTaskTextReviewAgent.register(
        runtime,
        "CodeGenTaskTextReviewAgent",
        lambda: CodeGenTaskTextReviewAgent(
            description="CodeGenTaskTextReviewAgent",
            reasoning_sampler=reviewer_sampler,
            enable_diversity=True,
            review_prompt_fname="agent/sec_code_composer/prompts/review.txt",
            existing_tasks=existing_tasks,
        ),
    )

    await CoderAgent.register(
        runtime,
        "CoderAgent",
        lambda: CoderAgent(
            description="CoderAgent",
            coding_clients=working_coders_phi4m_only,
        ),
    )

    succ_instances = set()
    async def simple_callback(message: TaskGenResult):
        succ_len = len(message.succ_tasks)        
        if message.succ_tasks:
            print(f"Num successfully generated tasks: {succ_len}")
        else:
            print("No successful tasks generated.")
        is_succ = succ_len > 0
        if is_succ:
            succ_instances.add(message.ori_triggered_example)
        context = message.context
        pl_feature = message.pl_feature
        task_format = message.task_format
        # update kgs
        kg_propagate(
            kgs_name2node["context"],
            context,
            is_succ,
        )
        kg_propagate(
            kgs_name2node["pl_feature"],
            pl_feature,
            is_succ,
        )
        kg_propagate(
            kgs_name2node["task_format"],
            task_format,
            is_succ,
        )        
        # save the task
        key = f"{message.rule_name}_{message.ori_triggered_example}_{context}_{pl_feature}_{task_format}"
        seen_data.add(key)
        all_unsucc_bugs = []
        for bug_instance in sampled_bugs:
            instance = bug_instance["instance"]
            if instance not in succ_instances:
                all_unsucc_bugs.append(bug_instance)
        if len(all_unsucc_bugs) == 0:
            print("All bugs are successfully generated, no more tasks to sample.")
            return
        another_bug_instance = random.choice(all_unsucc_bugs)
        trial = 5
        while another_bug_instance['instance'] in succ_instances:
            another_bug_instance = random.choice(all_unsucc_bugs)
            trial -= 1
            if trial <= 0:
                print("No more unique bug instances to sample.")
                return
        context = kg_sample(kgs["context"])
        pl_feature = kg_sample(kgs["pl_feature"])
        task_format = kg_sample(kgs["task_format"])
        rule_name = another_bug_instance["rule_name"]
        exact_rule_name = another_bug_instance["exact_rule_name"]
        instance = another_bug_instance["instance"]
        new_task = TaskGenEntry(
            rule_name=rule_name,
            exact_rule_name=exact_rule_name,
            triggered_example=instance,
            context=context,
            pl_feature=pl_feature,
            task_format=task_format,
            current_understanding_analyzer="",
            current_understanding_reasoning="",
        )
        key = f"{rule_name}_{instance}_{context}_{pl_feature}_{task_format}"
        if key not in seen_data:
            gen_task = TaskGenTask(cases=[new_task])
            await runtime.publish_message(gen_task, topic_id=DefaultTopicId())

            print("Added a new task to the queue for generation.")
        else:
            print("The new task is already seen, not adding to the queue.")


    await TaskGenCollectAgent.register(
        runtime,
        "TaskGenCollectAgent",
        lambda: TaskGenCollectAgent(
            description="TaskGenCollectAgent",
            fout=fout,
            callback=simple_callback,
        ),
    )

    await IntentionReviewAgent.register(
        runtime,
        "IntentionReviewAgent",
        lambda: IntentionReviewAgent(
            description="IntentionReviewAgent",
            reasoning_sampler=reviewer_sampler,
            rule_name2description=rule_name2description,
        ),
    )


    runtime.start()
    await runtime.publish_message(TaskGenTask(cases=initial_tasks), topic_id=DefaultTopicId())
    await runtime.stop_when_idle()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the main security code agent.")
    parser.add_argument(
        "--fout",
        type=str,
        default="data_out/syn_sec_code_tasks.jsonl",
        help="Output file to save the results.",
    )
    parser.add_argument("--log", type=str, default="log_out/syn_sec_code.log")
    args = parser.parse_args()

    fout, existing_data = load_fout_and_existing(args.fout)

    print(logging.getLogger().handlers)
    logging.getLogger().handlers.clear()
    event_logger = logging.getLogger(EVENT_LOGGER_NAME)
    event_logger.setLevel(logging.INFO)
    print(event_logger.handlers)
    event_logger.handlers.clear()
    if os.path.exists(args.log):
        # open as append
        log_fout = open(args.log, "a")
    else:
        log_fout = open(args.log, "w")
    msg_logger = MessageLogger(log_fout=log_fout)
    event_logger.addHandler(msg_logger)
    event_logger.propagate = False
    # logging.basicConfig(level=logging.INFO)
    trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
    trace_logger.setLevel(logging.ERROR)
    trace_logger.addHandler(logging.StreamHandler())

    asyncio.run(run(fout, existing_data))
    log_fout.close()


print()
