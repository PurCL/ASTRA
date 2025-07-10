
from typing import List
from tree_utils import get_all_expansion_paths, tree_loads, tree_dumps, TreeNode
from tqdm import tqdm
from enumerator import Enumerator
import os
import asyncio

starting_point = """
Help me enumerate potential programming context for python programs.

## Domain

Here is an example path in the hiearchy of features:

Layer0: Program Type: Library
Explanation: Layer0 describes the type of the program.
It can be a library, a standalone local service, a cli-program, a web client, or a web server.

Layer1: High-Level Use Scenario: Data processing
Explanation: Layer1 describes the major use scenario of a potential python program type.
In this example, a library can be used for data processing. A user can use it to process data in various ways.
Note that this layer includes only the high-level use scenario of the program type.
It should not be too specific or too detailed. It should be typical/reasonable use cases of the corresponding program type.

Layer2: Detailed Use Case: Data processing for deduplication
Explanation: Layer2 describes a more specific goal of the corresponding high-level use scenario.
It should be focus on the goal, not the implementation details.

Layer3: Instance: Data deduplication with embedding-based similarity search
Explanation: Layer3 provides a specific implementation of the detailed use case.
It is not necessary to specify the relevant libraries or tools used in the implementation.
But give a brief yet concise description of the implementation.
"""

MAX_LAYER = 4


fout_name = "kg/context.gen.kg"
if not os.path.exists(fout_name):
    fin = open("kg/context.kg", "r")
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
        batch_size = 50
        for i in range(0, len(paths_to_explore), batch_size):
            batch = paths_to_explore[i:i + batch_size]
            tasks = [asyncio.create_task(enumerate_one(path)) for path in batch]
            await asyncio.gather(*tasks)
            with open(fout_name, "w") as fout:
                fout.write(tree_dumps(root))
    asyncio.run(collect_all())


print()