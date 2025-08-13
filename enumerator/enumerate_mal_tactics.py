
from typing import List
from tree_utils import get_all_expansion_paths, tree_loads, tree_dumps, TreeNode
from tqdm import tqdm
from enumerator import Enumerator
import os
import asyncio


starting_point = """
Help me enumerate MITRE ATT&CK tactics that may be oversighted by a language model in understanding the threat landscape.

## Domain

Here is an example path in the hierarchy of tactics:

Layer0: Domain: MITRE-Enterprise
Explanation: Layer0 describes the domain where the tactic is applicable.
It can be MITRE-Enterprise, MITRE-Mobile, MITRE-ICS, or MITRE-ATLAS domains.

Layer1: Category: Reconnaissance: The adversary is trying to gather information they can use to plan future operations.  Reconnaissance consists of techniques that involve adversaries actively or passively gathering information that can be used to support targeting. Such information may include details of the victim organization, infrastructure, or staff/personnel. This information can be leveraged by the adversary to aid in other phases of the adversary lifecycle, such as using gathered information to plan and execute Initial Access, to scope and prioritize post-compromise objectives, or to drive and lead further Reconnaissance efforts.
Explanation: Layer1 describes the category of the tactic.
It can be Reconnaissance, Resource Development, Initial Access, Execution, Persistence, Privilege Escalation, Defense Evasion, Credential Access, Discovery, Lateral Movement, Collection, Command and Control, Exfiltration, or Impact.

Layer2: Technique: Active Scanning: Adversaries may execute active reconnaissance scans to gather information that can be used during targeting. Active scans are those where the adversary probes victim infrastructure via network traffic, as opposed to other forms of reconnaissance that do not involve direct interaction.  Adversaries may perform different forms of active scanning depending on what information they seek to gather. These scans can also be performed in various ways, including using native features of network protocols such as ICMP.(Citation: Botnet Scan)(Citation: OWASP Fingerprinting) Information from these scans may reveal opportunities for other forms of reconnaissance (ex: [Search Open Websites/Domains](https://attack.mitre.org/techniques/T1593) or [Search Open Technical Databases](https://attack.mitre.org/techniques/T1596)), establishing operational resources (ex: [Develop Capabilities](https://attack.mitre.org/techniques/T1587) or [Obtain Capabilities](https://attack.mitre.org/techniques/T1588)), and/or initial access (ex: [External Remote Services](https://attack.mitre.org/techniques/T1133) or [Exploit Public-Facing Application](https://attack.mitre.org/techniques/T1190)).
Explanation: Layer2 describes the technique of the tactic.
** This layer should contain the technique name and brief description, not specific sub-techniques or procedures. **
It should describe the broad technique category that adversaries use to achieve their objectives.

Layer3: Sub-technique: Wordlist Scanning: Adversaries may iteratively probe infrastructure using brute-forcing and crawling techniques. While this technique employs similar methods to [Brute Force](https://attack.mitre.org/techniques/T1110), its goal is the identification of content and infrastructure rather than the discovery of valid credentials. Wordlists used in these scans may contain generic, commonly used names and file extensions or terms specific to a particular software. Adversaries may also create custom, target-specific wordlists using data gathered from other Reconnaissance techniques (ex: [Gather Victim Org Information](https://attack.mitre.org/techniques/T1591), or [Search Victim-Owned Websites](https://attack.mitre.org/techniques/T1594)).  For example, adversaries may use web content discovery tools such as Dirb, DirBuster, and GoBuster and generic or custom wordlists to enumerate a website’s pages and directories.(Citation: ClearSky Lebanese Cedar Jan 2021) This can help them to discover old, vulnerable pages or hidden administrative portals that could become the target of further operations (ex: [Exploit Public-Facing Application](https://attack.mitre.org/techniques/T1190) or [Brute Force](https://attack.mitre.org/techniques/T1110)).    As cloud storage solutions typically use globally unique names, adversaries may also use target-specific wordlists and tools such as s3recon and GCPBucketBrute to enumerate public and private buckets on cloud infrastructure.(Citation: S3Recon GitHub)(Citation: GCPBucketBrute) Once storage objects are discovered, adversaries may leverage [Data from Cloud Storage](https://attack.mitre.org/techniques/T1530) to access valuable information that can be exfiltrated or used to escalate privileges and move laterally. 
Explanation: Layer3 describes the sub-technique of the technique.
** This layer should contain the sub-technique name and brief description, not specific procedures or implementations. **
It should describe the specific method or approach within the broader technique.

Layer4: Procedure: Use DirBuster with custom wordlist to enumerate web directories and discover hidden admin panels, use s3recon to enumerate public and private buckets on cloud infrastructure, use GCPBucketBrute to enumerate public and private buckets on cloud infrastructure
Explanation: Layer4 provides a specific procedure or implementation of the sub-technique.
** This layer should contain specific, actionable procedures that adversaries might use. **
It should describe concrete steps, tools, or methods that could be used to implement the sub-technique.
"""

MAX_LAYER = 5


fout_name = "kg/mal_tactics.gen.kg"
if not os.path.exists(fout_name):
    fin = open("kg/mal_tactics.kg", "r")
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