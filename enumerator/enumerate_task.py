
from typing import List
from tree_utils import get_all_expansion_paths, tree_loads, tree_dumps, TreeNode
from tqdm import tqdm
from enumerator import Enumerator
import os
import asyncio

starting_point = """
Help me enumerate potential coding tasks that a coding agent can help with.

## Domain

Here is an example path in the hiearchy of features:

Layer0: Task Nature: Major Modification
Explanation: Layer0 describes the nature of the task.
It can be generation, minor modification, or major modification.
Generation means that the agent generates code from scratch.
Minor modification means that the agent makes small changes to existing code.
Major modification means that the agent makes significant changes to existing code.

Layer1: Form: NL+Code to Code
Explanation: Layer1 describes the form of the task (what is in the input and output).
Only give high-level description of the form.

Layer2: Detailed Task: Refactor code to improve readability, by renaming variables
Explanation: Layer2 describes a specific task that the agent can help with.
"""

MAX_LAYER = 3


fout_name = "kg/task.gen.kg"
if not os.path.exists(fout_name):
    fin = open("kg/task.kg", "r")
    tree_str = fin.read()
    fin.close()
    root = tree_loads(tree_str)
    with open(fout_name, "w") as fout:
        fout.write(tree_dumps(root))
else:
    fin = open(fout_name, "r")
    tree_str = fin.read()
    fin.close()
    root = tree_loads(tree_str)


paths_to_explore = get_all_expansion_paths(root)
paths_to_explore = [p for p in paths_to_explore if len(p) < MAX_LAYER]
rnd = 0
while len(paths_to_explore) > 0:
    paths_to_explore = get_all_expansion_paths(root)
    paths_to_explore = [p for p in paths_to_explore if len(p) < MAX_LAYER]
    pbar = tqdm(total=len(paths_to_explore), desc="Enumerating paths, round %d" % rnd)
    rnd += 1
    async def enumerate_one(current_path):
        current_enumerator = Enumerator(current_path, starting_point, pbar=False)
        ret = await asyncio.to_thread(current_enumerator.start_enumerate, budget=10)
        leaf_node = current_path[-1]
        is_last_layer = len(current_path) == MAX_LAYER - 1
        for r in ret:
            new_node = TreeNode(name=r)
            if not is_last_layer:
                new_node.add_expansion_hint()
            leaf_node.add_child(new_node)
        leaf_node.remove_expansion_hint()
        pbar.update(1)
        return
    async def collect_all():
        tasks = []
        batch_size = 200
        for i in range(0, len(paths_to_explore), batch_size):
            batch = paths_to_explore[i:i + batch_size]
            tasks = [asyncio.create_task(enumerate_one(path)) for path in batch]
            await asyncio.gather(*tasks)
    asyncio.run(collect_all())

    with open(fout_name, "w") as fout:
        fout.write(tree_dumps(root))

print()