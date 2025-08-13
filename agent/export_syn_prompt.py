import argparse
import json
import copy

parser = argparse.ArgumentParser()
parser.add_argument(
    "--fin", default="data_out/syn_sec_event_tasks.jsonl"
)
parser.add_argument(
    "--fout", default=""
)
parser.add_argument(
    "--key", default="rationale", 
    help="key to export, rationale for sec_code and goal for sec_event"
)

args = parser.parse_args()

if args.fout == "":
    args.fout = args.fin.replace(".jsonl", "_export.jsonl")

data_in = [json.loads(line) for line in open(args.fin, "r")]

data_out = []
for item in data_in:
    item_copied = copy.deepcopy(item)
    del item_copied["session_id"]
    del item_copied["raw_prompt"]
    del item_copied["raw_rsp"]
    to_remove_keys = set()
    for k, v in item_copied.items():
        if k.startswith("current_understanding") or k.endswith("_tasks"):
            to_remove_keys.add(k)
    for k in to_remove_keys:
        del item_copied[k]
    del item_copied['all_triggered_examples_w_reasoning']
    del item_copied['type_name']
    
    succ_tasks = set(item["succ_tasks"])

    for task in item["all_triggered_examples_w_reasoning"]:
        if task["task"] not in succ_tasks:
            continue
        task_str = task["task"]
        if args.key in task:
            rationale = task[args.key]
        else:
            rationale = 'N/A'
        
        data_out.append({
            'task': task_str,
            args.key: rationale,
            **item_copied
        })
            
data_out = [d for d in data_out if d[args.key].strip() != '']

with open(args.fout, "w") as fout:
    for item in data_out:
        fout.write(json.dumps(item) + "\n")

print()