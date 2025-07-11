
from typing import List
from tree_utils import get_all_expansion_paths, tree_loads, tree_dumps, TreeNode
from tqdm import tqdm
from enumerator import Enumerator
import os
import asyncio


starting_point = """
Help me enumerate assets that may be targeted by malicious cyber activities based on MITRE ATT&CK framework.

## Domain

Here is an example path in the hierarchy of target assets:

Layer0: Asset Domain: ICS
Explanation: Layer0 describes the broadest category representing the overall environment or sector that may be targeted by malicious cyber activities.
** This layer should contain the domain name and brief description, not specific asset types. **
It should describe the major sectors or environments (e.g., ICS, Enterprise, Cloud, OT) that adversaries might target.

Layer1: Asset Type: Application Server
Explanation: Layer1 describes a major class of assets within the domain that may be exploited by attackers.
** This layer should contain the asset type name and brief description, not specific sub-types. **
It should describe the primary categories of assets (e.g., servers, workstations, network devices, databases) available in the target domain.

Layer2: Asset Sub-type: SCADA Historian Server
Explanation: Layer2 describes a more specific category of assets that may be leveraged by malicious actors.
** This layer should contain the sub-type name and brief description, not specific instances. **
It should describe specific types of assets within the broader asset type that adversaries might target.

Layer3: Asset Instance: HistorianServer01 (IP: 10.1.2.3)
Explanation: Layer3 describes a concrete, real-world instance of the asset that may create attack vectors.
** This layer should contain specific, actionable instances that exist in the environment. **
It should describe concrete examples of assets with unique identifiers, configurations, or characteristics that adversaries might target.
"""
MAX_LAYER = 4


fout_name = "kg/mal_asset.gen.kg"
if not os.path.exists(fout_name):
    fin = open("kg/mal_asset.kg", "r")
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