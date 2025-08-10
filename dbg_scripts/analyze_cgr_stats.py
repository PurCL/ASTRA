import json

data_in = [json.loads(line) for line in open("data_out/syn_sec_code_tasks-phi4m-only_export-inference-cgr.jsonl", "r").readlines()]

num_triggered = [e for e in data_in if e['__cgr_ret']['trigger']]
num_not_triggered = [e for e in data_in if not e['__cgr_ret']['trigger']]


print()