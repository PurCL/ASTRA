import json
from rt.data_modeling import VulCodePromptDO

all_vul_code_prompts = [
    VulCodePromptDO(**json.loads(line)) for line in open("data_out/syn_sec_code_tasks_export.jsonl", "r")
]

print()