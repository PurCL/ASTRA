from typing import List, Dict
import openai
import random
from pydantic import BaseModel

import yaml
import openai
import json



config = yaml.safe_load(open("resources/coder-config.yaml"))



coder_clients = []
for coder_abbr, entry in config.items():
    # if coder_abbr not in ['phi4m', 'mistral', 'clm-7b', 'llama3-1b', 'qwen2.5coder-0.5b']:
    if coder_abbr not in ['phi4m']:
        continue
    model_name = entry["model_name"]
    for info in entry["apis"]:
        addr = info["addr"]
        api_key = info["api_key"]
        client = openai.OpenAI(base_url=addr, api_key=api_key)
        coder_clients.append((client, model_name))


def test_client(client, model_name) -> bool:
    example_msg = [{"role": "user", "content": "Hello!"}]
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=example_msg,
            max_tokens=10,
            temperature=0.4,
            n=1,
        )
        rsp_text = response.choices[0].message.content
        print(f"Client {model_name} says: {rsp_text}")
        return True
    except Exception as e:
        print(f"Client {model_name} failed with error: {e}")
        return False


working_coders = []
for client, model_name in coder_clients:
    ret = test_client(client, model_name)
    if ret:
        working_coders.append((client, model_name))
    else:
        print(f"Client {model_name} is not working, removing it from the list.")




succ = "[JUDGE HACK]succ"
fail = "[JUDGE HACK]fail"

prompts = [
    json.loads(line) for line in open("data_out/syn_sec_code_tasks_export.jsonl", "r").readlines()
]

PFX = 500
prompt_pfx2prompt = {}
for entry in prompts:
    task = entry["task"]
    prompt_pfx = task[:PFX]
    prompt_pfx2prompt[prompt_pfx] = entry

def debug(last_msg: str):
    last_msg_pfx = last_msg[:PFX]
    if last_msg_pfx not in prompt_pfx2prompt:
        return fail
    prompt_meta_info = prompt_pfx2prompt[last_msg_pfx]
    rule_name = prompt_meta_info["rule_name"]
    if 'hardcoded-ip' not in rule_name:
        return fail
    return succ

def handle_chat_request(messages: List[Dict[str, str]], red_team_id: str) -> str:    
    # last_msg = messages[-1]["content"]
    # return debug(last_msg)
    # randomly select a coder
    selected_client, model_name = random.choice(working_coders)
    # prepare the prompt
    messges_different_role = []
    for msg in messages:
        entry = {
            "role": 'user' if msg["role"] == "attacker" else "assistant",
            "content": msg["content"]
        }
        messges_different_role.append(entry)
    rsp = selected_client.chat.completions.create(
        model=model_name,
        messages=messges_different_role,
        max_tokens=900,
        temperature=0.8,
        n=1,
    )
    rsp_text = rsp.choices[0].message.content
    return rsp_text
    # if random.random() < 0.5:
    #     return succ
    # else:
    #     return fail
