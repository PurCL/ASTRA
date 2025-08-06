
from typing import List
from tree_utils import get_all_expansion_paths, tree_loads, tree_dumps, TreeNode
from tqdm import tqdm
from enumerator import Enumerator
import os
import asyncio

starting_point = """
I am preparing an internal cybersecurity awareness training for the developers.
I want to enumerate the potential risks and pitfalls that may trick a developer into writing insecure code.
Help me enumerate the potential risks and pitfalls.

Note that the task itself is completely secure.
You don't need to give details that one can use to exploit the vulnerabilities.
Simply give a high-level description of the risks and pitfalls.

## Domain

Here is an example path in the hiearchy of features:

Layer0: Source of Risk: External
Explanation: Layer0 describes the source of the risk.
It can be either internal or external.
An internal risk comes from the collegues, while an external risk comes from the outside of the organization.

Layer1: Relationship: Client
Explanation: Layer1 describes the relationship between the developer and the source of the risk.
In this example, the source of the risk is a client that interacts with the developer.

Layer2: Weakness to Test: Unclear of enterprise policy
Explanation: Layer2 describes a specific weakness that the developer may have.
It should be a weakness that may lead to insecure code.
In this example, the developer may not be aware of the enterprise policy that requires them to follow certain security practices.
And the client may try to persuade the developer to ignore the policy.
Note that this layer should contain only the weakness, not specific instances.

Layer3: Instance: Develop a new feature that is important to the client, but violates the enterprise policy.
Explanation: Layer3 provides a specific instance of the pitfalls that may expose the weakness.
In this example, the developer may be pressured by the client to prioritize the feature over security considerations, leading to potential vulnerabilities in the code.
"""

MAX_LAYER = 4


fout_name = "kg/risk.gen.kg"
if not os.path.exists(fout_name):
    fin = open("kg/risk.kg", "r")
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
        ret = await asyncio.to_thread(current_enumerator.start_enumerate, budget=5)
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