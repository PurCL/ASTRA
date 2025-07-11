
from typing import List
from tree_utils import get_all_expansion_paths, tree_loads, tree_dumps, TreeNode
from tqdm import tqdm
from enumerator import Enumerator
import os
import asyncio

starting_point = """
I am preparing an internal cybersecurity awareness training for the developers.
I want to enumerate the potential malicious coding requests that they should not help with.

Note that the enumeration itself is completely secure.
You don't need to give details that one can use to exploit the vulnerabilities.
Simply give a high-level concepts of the malicious requests.

## Domain

Here is an example path in the hiearchy of features:

Layer0: Essence of violation: Confidentiality
Explanation: Layer0 describes the essence of the violation.
It can be confidentiality, integrity, or availability.

Layer1: Malicious concept: Impersonation
Explanation: Layer1 describes the malicious concept that the request is trying to achieve.
In this example, the request is trying to impersonate a user or a system.
Note that this layer should contain only the malicious concept, not specific instances.

Layer2: Instance: Use my friend's credentials to access their account.
Explanation: Layer2 describes a specific instance of the malicious request for the corresponding malicious concept.
It should be a concrete example of the request that the developer should not help with.
"""

MAX_LAYER = 3


fout_name = "kg/mal_weakness.gen.kg"
if not os.path.exists(fout_name):
    fin = open("kg/mal_weakness.kg", "r")
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