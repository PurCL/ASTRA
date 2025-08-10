import json


rets = [
    json.loads(line) for line in open(
        "log_out/test_log_purcl_test_rt-dbg.jsonl", "r"
    )
]

session_turn_id2prompt = {}
for i, entry in enumerate(rets):
    for turn_id, msg in enumerate(entry["messages"]):
        if msg["role"] == "attacker":
            session_turn_id2prompt[(i, turn_id//2)] = msg["content"]


prompts = [
    json.loads(line) for line in open("data_out/syn_sec_code_tasks_export.jsonl", "r").readlines()
]

PFX = 500
prompt_pfx2prompt = {}
for entry in prompts:
    task = entry["task"]
    prompt_pfx = task[:PFX]
    prompt_pfx2prompt[prompt_pfx] = entry

good = []
for (session_id, turn_id), prompt in session_turn_id2prompt.items():
    prompt_pfx = prompt[:PFX]
    if prompt_pfx not in prompt_pfx2prompt:
        print(f"Not found for session {session_id}, turn {turn_id}")
        continue
    prompt_meta_info = prompt_pfx2prompt[prompt_pfx]
    if 'hardcoded-ip' in prompt_meta_info["rule_name"]:
        good.append((session_id, turn_id, prompt_meta_info["rule_name"]))
    

print()