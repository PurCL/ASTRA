
from typing import List
from tree_utils import get_all_expansion_paths, tree_loads, tree_dumps, TreeNode
from tqdm import tqdm
from enumerator import Enumerator
import os
import asyncio

starting_point = """
Help me enumerate python program language features that may introduce challenges to a language model
in precisely understanding code semantics.

## Domain

Here is an example path in the hiearchy of features:

Layer0: Category: Data-flow features
Explanation: Layer0 describes the category of complexity.
It can be data-flow or control-flow features.

Layer1: Scope: Intra-procedural features
Explanation: Layer1 describes the scope of the features.
It can be intra-procedural or inter-procedural features.

Layer2: Nature of challenge: A model may have difficulty understanding data flow across variables with similar names.
Explanation: Layer2 describes the nature of the challenge.
It should be an essential challenge to a language model in understanding code semantics.
** This layer should contain only the nature of the challenge, not specific instances. **
It should describe the challenges caused by the limitation of a model, not the detailed instances.

Layer3: Instance: Variable shadowing. (e.g., a variable is defined in a nested scope with the same name as a variable in an outer scope)
Explanation: Layer3 provides a specific instance of the challenge.
"""

MAX_LAYER = 4


fout_name = "kg/pl_features.gen.kg"
if not os.path.exists(fout_name):
    fin = open("kg/pl_features.kg", "r")
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
        for current_path in paths_to_explore:
            tasks.append(asyncio.create_task(enumerate_one(current_path)))
        return await asyncio.gather(*tasks)
    asyncio.run(collect_all())

    with open(fout_name, "w") as fout:
        fout.write(tree_dumps(root))

print()