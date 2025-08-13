import os
import json
import yaml
from tree_utils import TreeNode, tree_dumps
from stix2 import FileSystemSource
from mitre_utils import subtechniques_of, getTacticsByMatrix, get_tactic_techniques 

# clone https://github.com/mitre/cti and specify the path
PATH_TO_CTI = "path/to/cti"
# clone https://github.com/mitre-atlas/atlas-data and specify the path
PATH_TO_ATLAS = "path/to/atlas"

if PATH_TO_ATLAS == "path/to/atlas" or PATH_TO_CTI == "path/to/cti":
    raise ValueError("Please specify the correct path to the CTI and ATLAS data repositories.")

cti_data_source = {
    "MITRE-Enterprise": {"dir": f"{PATH_TO_CTI}/enterprise-attack", "kill_chain_name": "mitre-attack"},
    "MITRE-Mobile": {"dir": f"{PATH_TO_CTI}/mobile-attack", "kill_chain_name": "mitre-mobile-attack"},
    "MITRE-ICS": {"dir": f"{PATH_TO_CTI}/ics-attack", "kill_chain_name": "mitre-ics-attack"},
}


atlas_data_source = {
    "MITRE-ATLAS": f"{PATH_TO_ATLAS}/dist/ATLAS.yaml",
}


root = TreeNode("Root")
for data_source_name, data_source_info in cti_data_source.items():
    data_source_node = TreeNode(data_source_name)
    root.add_child(data_source_node)
    src = FileSystemSource(data_source_info["dir"])
    subtechnique_map = subtechniques_of(src)
    tactics = getTacticsByMatrix(src)
    for source, tactics in tactics.items():
        for tactic in tactics:
            tactic_shortname = tactic["x_mitre_shortname"]
            techniques = get_tactic_techniques(src, tactic_shortname, data_source_info["kill_chain_name"])
            tactic_node_name = tactic_shortname + ": " + tactic["description"].replace("\n", " ")
            tactic_node = TreeNode(tactic_node_name)
            data_source_node.add_child(tactic_node)
            for technique in techniques:
                technique_id = technique["id"]
                technique_name = technique["name"]
                technique_description = technique["description"].replace("\n", " ")
                technique_node_name = technique_name + ": " + technique_description
                technique_node = TreeNode(technique_node_name)
                tactic_node.add_child(technique_node)
                subtechniques = subtechnique_map.get(technique_id, [])
                if len(subtechniques) > 0:
                    for subtechnique in subtechniques:
                        subtechnique_id = subtechnique["object"]["id"]
                        subtechnique_name = subtechnique["object"]["name"]
                        subtechnique_description = subtechnique["object"]["description"].replace("\n", " ")
                        subtechnique_node_name = subtechnique_name + ": " + subtechnique_description
                        subtechnique_node = TreeNode(subtechnique_node_name)
                        subtechnique_node.add_expansion_hint()
                        technique_node.add_child(subtechnique_node)
                else:
                    technique_node.add_expansion_hint()



# parse atlas data
for data_source_name, data_source_path in atlas_data_source.items():
    data_source_node = TreeNode(data_source_name)
    root.add_child(data_source_node)
    with open(data_source_path, "r") as f:
        data = yaml.safe_load(f)
        matrics = data["matrices"][0]
        tactics = matrics["tactics"]
        techniques = matrics["techniques"]
        for tactic in tactics:
            tactic_id = tactic["id"]
            tactic_shortname = tactic["name"]
            tactic_description = tactic["description"].replace("\n", " ")
            node_name = tactic_shortname + ": " + tactic_description
            tactic_node = TreeNode(node_name)
            data_source_node.add_child(tactic_node)

            
            tactic_techniques = [] 
            for technique in techniques:
                if technique.get("tactics", None) is None:
                    continue
                if any(tactic_id in t for t in technique.get("tactics", None)):
                    tactic_techniques.append(technique)
            
            
            for technique in tactic_techniques:
                technique_id = technique["id"]
                technique_name = technique["name"]
                technique_description = technique["description"].replace("\n", " ")
                node_name = technique_name + ": " + technique_description
                technique_node = TreeNode(node_name)
                tactic_node.add_child(technique_node)

                
                tactic_subtechniques = []
                for subtechnique in techniques:
                    subtechnique_of = subtechnique.get("subtechnique-of", None)
                    if subtechnique_of is None:
                        continue
                    if subtechnique_of == technique_id:
                        tactic_subtechniques.append(subtechnique)
                
                if len(tactic_subtechniques) > 0:
                    for subtechnique in tactic_subtechniques:
                        subtechnique_id = subtechnique["id"]
                        subtechnique_name = subtechnique["name"]
                        subtechnique_description = subtechnique["description"].replace("\n", " ")
                        node_name = subtechnique_name + ": " + subtechnique_description
                        subtechnique_node = TreeNode(node_name)
                        subtechnique_node.add_expansion_hint()
                        technique_node.add_child(subtechnique_node)
                        
                else:
                    technique_node.add_expansion_hint()

# write tree to file using tree_dumps
with open("kg/mal_tactics.kg", "w") as f:
    f.write(tree_dumps(root))