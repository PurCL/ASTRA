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
from tqdm import tqdm
from utils import get_claude_completion_adapter, remove_py_comments
from kg_utils import tree_loads, TreeNode
import random

from sec_event_composer import (
    SecEventTaskGenEntry,
    TaskGenTask,
    TaskGenResult,
    TaskDispatchConfigure,
    TaskComposingDispatchAgent,
    CodeGenTaskComposingAgent,
    TaskIntentionReviewAgent,
    HelpfulnessReviewAgent,
    CoderAgent,
    TaskGenCollectAgent,
)
from log_utils import MessageLogger
from itertools import product

# reimport the llm client utils to ensure the sampler is set up correctly


kgs_fin = {
    "context": "kg/context.gen.kg",
    # "pl_feature": "kg/pl_features.gen.kg",
    "task_format": "kg/task.gen.kg",
    "asset": "kg/mal_asset.gen.kg",
    "software": "kg/mal_software.gen.kg",
    "tactics": "kg/mal_tactics.gen.kg",
    "weakness": "kg/mal_weakness.gen.kg",
}

kgs = {}
for kg_name, kg_path in tqdm(kgs_fin.items(), desc="Loading knowledge graphs"):
    if os.path.exists(kg_path):
        with open(kg_path, "r") as f:
            kgs[kg_name] = tree_loads(f.read())
    else:
        logging.warning(
            f"KG file {kg_path} does not exist. Skipping loading for {kg_name}."
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

random.seed(42)
sampled_leaves = {k: random.sample(v, min(5, len(v))) for k, v in kg_leaves.items()}
task_list = []

# Create all combinations of sampled leaves
combinations = product(
    sampled_leaves["context"],
    sampled_leaves["task_format"], 
    sampled_leaves["asset"],
    sampled_leaves["software"],
    sampled_leaves["tactics"],
    sampled_leaves["weakness"]
)

task_list = [
    SecEventTaskGenEntry(
        context=context.name,
        task_format=task_format.name,
        asset=asset.name,
        software=software.name,
        tactics=tactics.name,
        weakness=weakness.name,
    )
    for context, task_format, asset, software, tactics, weakness in combinations
]


random.seed(42)
# shuffle
random.shuffle(task_list)

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
        context = task["context"]
        task_format = task["task_format"]
        asset = task["asset"]
        software = task["software"]
        tactics = task["tactics"]
        weakness = task["weakness"]
        key = f"{context}_{task_format}_{asset}_{software}_{tactics}_{weakness}"
        if len(task["succ_tasks"]) > 0:
            select_one = random.choice(task["succ_tasks"])
            existing_tasks.append(select_one)
            seen.add(key)

    to_explore = []
    for task in task_list:
        context = task.context
        task_format = task.task_format
        asset = task.asset
        software = task.software
        tactics = task.tactics
        weakness = task.weakness
        key = f"{context}_{task_format}_{asset}_{software}_{tactics}_{weakness}"
        if key in seen:
            continue
        
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
            gen_prompt_fname="agent/sec_event_composer/prompts/compose.txt",
        ),
    )

    await TaskIntentionReviewAgent.register(
        runtime,
        "TaskIntentionReviewAgent",
        lambda: TaskIntentionReviewAgent(
            description="TaskIntentionReviewAgent",
            reasoning_sampler=reviewer_sampler,
            enable_diversity=True,
            review_prompt_fname="agent/sec_event_composer/prompts/intention_review.txt",
            existing_tasks=existing_tasks,
        ),
    )

    await CoderAgent.register(
        runtime,
        "CoderAgent",
        lambda: CoderAgent(
            description="CoderAgent",
            coding_clients=working_coders,
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

    await HelpfulnessReviewAgent.register(
        runtime,
        "HelpfulnessReviewAgent",
        lambda: HelpfulnessReviewAgent(
            description="HelpfulnessReviewAgent",
            reasoning_sampler=reviewer_sampler,
        ),
    )

    initial_task = TaskGenTask(cases=to_explore)

    runtime.start()
    await runtime.publish_message(initial_task, topic_id=DefaultTopicId())
    await runtime.stop_when_idle()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the main security code agent.")
    parser.add_argument(
        "--fout",
        type=str,
        default="data_out/syn_sec_event_tasks.jsonl",
        help="Output file to save the results.",
    )
    parser.add_argument("--log", type=str, default="log_out/syn_sec_event.log")
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

    asyncio.run(run(task_list, fout, existing_data))
    log_fout.close()


print()
