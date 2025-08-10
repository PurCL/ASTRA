import json
import numpy as np
from kg_utils import tree_loads, TreeNode

data_in = [
    json.loads(line)
    for line in open("data_out/syn_sec_code_tasks-phi4m-only.jsonl", "r")
]


all_num_tasks = []
succ_num_tasks = []
for item in data_in:
    fail_tasks = item['fail_to_trigger_tasks']
    succ_tasks = item['succ_tasks']
    if len(succ_tasks) > 0:
        succ_num_tasks.append(len(fail_tasks))
    all_num_tasks.append(len(fail_tasks))





kgs_fin = {
    "context": "kg/context.gen.kg",
    "pl_feature": "kg/pl_features.gen.kg",
    "task_format": "kg/task.gen.kg",
}

kgs = {}
for kg_name, kg_path in kgs_fin.items():    
    with open(kg_path, "r") as f:
        kgs[kg_name] = tree_loads(f.read())

rules = json.load(open("resources/rules.json"))

rule_name2description = {
    v["ruleManifestId"]: v["longDescription"] for v in rules.values()
}

rule_name2exact_rule_name = json.load(open("resources/rule_name2exact_rule_name.json"))

bug_type = json.load(open("kg/bugtype.kg.json"))

kg2name2node = {}
for kg_name, kg in kgs.items():
    kg2name2node[kg_name] = {}
    # dfs
    def dfs(node: TreeNode):
        if not node.children:  # If no children, it's a leaf node
            kg2name2node[kg_name][node.name] = node
        else:
            for child in node.children:
                dfs(child)
    dfs(kg)

def update_kg(kg, name, is_succ):
    if name not in kg2name2node[kg]:
        print("Error: Node not found in KG:", name)
        return
    node = kg2name2node[kg][name]
    def _update_parent(node, is_succ):
        if is_succ:
            node.succ += 1            
        else:
            node.fail += 1
        if node.parent:
            _update_parent(node.parent, is_succ)
    _update_parent(node, is_succ)
    

dim2tag2cnt = {
    'context': {},
    'pl_feature': {},
    'task_format': {},
    'rule_name': {},
}
for item in data_in:
    context = item['context']
    rule_name = item['rule_name']
    pl_feature = item['pl_feature']
    task_format = item['task_format']
    if context not in dim2tag2cnt['context']:
        dim2tag2cnt['context'][context] = {
            'all': 0,
            'succ': 0,
            'fail': 0,
        }
    if rule_name not in dim2tag2cnt['rule_name']:
        dim2tag2cnt['rule_name'][rule_name] = {
            'all': 0,
            'succ': 0,
            'fail': 0,
        }
    if pl_feature not in dim2tag2cnt['pl_feature']:
        dim2tag2cnt['pl_feature'][pl_feature] = {
            'all': 0,
            'succ': 0,
            'fail': 0,
        }
    if task_format not in dim2tag2cnt['task_format']:
        dim2tag2cnt['task_format'][task_format] = {
            'all': 0,
            'succ': 0,
            'fail': 0,
        }
    dim2tag2cnt['context'][context]['all'] += 1
    dim2tag2cnt['rule_name'][rule_name]['all'] += 1
    dim2tag2cnt['pl_feature'][pl_feature]['all'] += 1
    dim2tag2cnt['task_format'][task_format]['all'] += 1
    if len(item['succ_tasks']) > 0:
        dim2tag2cnt['context'][context]['succ'] += 1
        dim2tag2cnt['rule_name'][rule_name]['succ'] += 1
        dim2tag2cnt['pl_feature'][pl_feature]['succ'] += 1
        dim2tag2cnt['task_format'][task_format]['succ'] += 1
    else:
        dim2tag2cnt['context'][context]['fail'] += 1
        dim2tag2cnt['rule_name'][rule_name]['fail'] += 1
        dim2tag2cnt['pl_feature'][pl_feature]['fail'] += 1
        dim2tag2cnt['task_format'][task_format]['fail'] += 1
    succ = len(item['succ_tasks']) > 0
    update_kg('context', context, succ)
    update_kg('pl_feature', pl_feature, succ)
    update_kg('task_format', task_format, succ)
    # update_kg('rule_name', rule_name, succ)


def sort_dim(dim2tag2cnt, dim):
    sorted_items = sorted(dim2tag2cnt[dim].items(), key=lambda x: x[1]['succ'], reverse=True)
    return [(k, v) for k, v in sorted_items]


sorted_context = sort_dim(dim2tag2cnt, 'context')
sorted_rule_name = sort_dim(dim2tag2cnt, 'rule_name')
sorted_pl_feature = sort_dim(dim2tag2cnt, 'pl_feature')
sorted_task_format = sort_dim(dim2tag2cnt, 'task_format')



print()
