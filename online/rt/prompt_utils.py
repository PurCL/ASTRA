import json
from rt.data_modeling import VulCodePromptDO, SecEventPromptDO

all_vul_code_prompts = [
    VulCodePromptDO(**json.loads(line)) for line in open("data_out/syn_sec_code_tasks-phi4m-only_export.jsonl", "r")
]

all_sec_event_prompts = [
    SecEventPromptDO(**json.loads(line)) for line in open("data_out/syn_sec_event_tasks-phi4m-only_export.jsonl", "r")
]

print()