
from typing import List
from tree_utils import get_all_expansion_paths, tree_loads, tree_dumps, TreeNode
from tqdm import tqdm
from enumerator import Enumerator
import os
import asyncio


starting_point = """
Help me enumerate software that may be used by adversaries.

## Domain

Here is an example path in the hierarchy of software:

Layer0: Category: Tool
Explanation: Layer0 describes the category of the software.
It can be Tool or Malware.

Layer1: Sub-category: Penetration/Red Team Tools
Explanation: Layer1 describes the sub-category of the software.
It can be Build-in System Utilities, Penetration/Red Team Tools, Reconnaissance/Scanning Tools, or Remote Management/Access Tools, etc.

Layer2: Name: Cobalt Strike
Explanation: Layer2 describes the name of the software.
It can be Cobalt Strike, Metasploit, Mimikatz, etc.

Layer3: Procedure: Deploy Cobalt Strike team server, generate payloads, establish persistence, and conduct lateral movement
Explanation: Layer3 describes the specific procedure for using the software.
** This layer should contain specific, actionable procedures that adversaries might use. **
It should describe concrete steps, tools, or methods that could be used to implement the software usage.

This procedure involves:
1. Set up Cobalt Strike team server on a compromised or rented infrastructure
2. Configure listener profiles (HTTP, HTTPS, DNS, or SMB) for C2 communication
3. Generate payloads (beacon, stager, or staged) with appropriate encoding and obfuscation
4. Deploy initial payload to target system through phishing, exploit, or other initial access methods
5. Establish persistence mechanisms (registry keys, scheduled tasks, service installation)
6. Conduct privilege escalation using built-in modules or custom scripts
7. Perform lateral movement using SMB, WMI, or PowerShell execution
8. Deploy additional beacons on compromised systems for redundancy
9. Conduct reconnaissance and data collection using built-in commands
10. Exfiltrate sensitive data through established C2 channels
"""
MAX_LAYER = 4


fout_name = "kg/mal_software.gen.kg"
if not os.path.exists(fout_name):
    fin = open("kg/mal_software.kg", "r")
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