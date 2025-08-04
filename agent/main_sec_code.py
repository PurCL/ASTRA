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
from kg_utils import tree_loads, TreeNode
import random

from composer_agent import (
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
    TaskGenCollectAgent
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
            sampled_bugs.append(
                {
                    "rule_name": rule_name,
                    "exact_rule_name": exact_rule_name,
                    "instance": random.choice(instances),
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


kg_leaves = {k: _get_leaf_nodes_from_kg(v) for k, v in kgs.items()}


task_list = []
random.seed(42)
for bug in sampled_bugs:
    rule_name = bug["rule_name"]
    exact_rule_name = bug["exact_rule_name"]
    instance = bug["instance"]

    if rule_name not in rules:
        logging.warning(f"Rule {rule_name} not found in rules.json")
        continue

    context = random.choice(kg_leaves["context"]).name
    pl_feature = random.choice(kg_leaves["pl_feature"]).name
    task_format = random.choice(kg_leaves["task_format"]).name
    task_list.append(
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

def load_fout_and_existing(fout_name):

    if not os.path.exists(fout_name):
        existing_data = []
        fout = open(fout_name, "w")
    else:
        existing_data = [json.loads(line) for line in open(fout_name, "r")]
        fout = open(fout_name, "a")
    return fout, existing_data



async def run(task_list, fout, existing_data):

    seen = set()
    existing_tasks = []
    for task in existing_data:
        rule_name = task["rule_name"]
        example = task["triggered_example"]
        context = task["context"]
        pl_feature = task["pl_feature"]
        task_format = task["task_format"]
        key = f"{rule_name}_{example}_{context}_{pl_feature}_{task_format}"
        if len(task['succ_tasks']) > 0:
            select_one = random.choice(task['succ_tasks'])
            existing_tasks.append(select_one)
            seen.add(key)

    to_explore = []
    for task in task_list:
        rule_name = task.rule_name
        example = task.triggered_example
        context = task.context
        pl_feature = task.pl_feature
        task_format = task.task_format
        key = f"{rule_name}_{example}_{context}_{pl_feature}_{task_format}"

        if key not in seen:
            to_explore.append(task)
    from llm_client_utils import get_sampler, working_coders
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
            gen_prompt_fname="agent/composer_agent/prompts/compose.txt",
        ),
    )

    await CodeGenTaskTextReviewAgent.register(
        runtime,
        "CodeGenTaskTextReviewAgent",
        lambda: CodeGenTaskTextReviewAgent(
            description="CodeGenTaskTextReviewAgent",
            reasoning_sampler=reviewer_sampler,
            enable_diversity=True,
            review_prompt_fname="agent/composer_agent/prompts/review.txt",
            existing_tasks=existing_tasks,
        ),
    )

    await CoderAgent.register(
        runtime,
        "CoderAgent",
        lambda: CoderAgent(
            description="CoderAgent",
            coding_clients= working_coders,
        ),
    )

    def simple_callback(message: TaskGenResult):   
        succ_len = len(message.succ_tasks)     
        if message.succ_tasks:
            print(f"Num successfully generated tasks: {succ_len}")
        else:
            print("No successful tasks generated.")

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
            rule_name2description=rules,
        ),
    )

    initial_task = TaskGenTask(cases=to_explore)

    runtime.start()
    await runtime.publish_message(initial_task, topic_id=DefaultTopicId())
    await runtime.stop_when_idle()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the main security code agent.")
    parser.add_argument("--fout", type=str, default="data_out/syn_sec_code_tasks.jsonl",
                        help="Output file to save the results.")
    parser.add_argument("--log", type=str, default="log_out/syn_sec_code.log")
    args = parser.parse_args()

    log_fout, existing_data = load_fout_and_existing(args.fout)


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

    asyncio.run(run(task_list, log_fout, existing_data))
    log_fout.close()




print()
