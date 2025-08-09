import boto3
import os
import json
import time
import boto3.dynamodb
import boto3.dynamodb.conditions
from tqdm import tqdm
from pydantic import BaseModel
import argparse
import asyncio
import openai
import yaml
from cgr_helper import test_code, test_code_w_rule_details
import random


parser = argparse.ArgumentParser()
parser.add_argument("--fin", default="data_out/syn_sec_code_tasks_export-inference.jsonl")
parser.add_argument("--fout", default="")

args = parser.parse_args()

if args.fout == "":
    args.fout = args.fin.replace(".jsonl", "-cgr.jsonl")

rule_name2exact_rule_name = json.load(
    open("resources/rule_name2exact_rule_name.json", "r")
)


data_in = [json.loads(line) for line in open(args.fin, "r").readlines()]

if os.path.exists(args.fout):
    existing_data = [json.loads(line) for line in open(args.fout, "r").readlines()]
    existing_prompts = set()
    for entry in existing_data:
        prompt = entry["task"]
        existing_prompts.add(prompt)
    fout = open(args.fout, "a")
else:
    existing_prompts = set()
    fout = open(args.fout, "w")

to_process = []
for entry in data_in:
    prompt = entry["task"]
    if prompt in existing_prompts:
        continue
    to_process.append(entry)

pbar = tqdm(total=len(to_process), desc="Processing entries")
on_going = set()

async def process_entries(entries):
    global fout
    global pbar
    global on_going
    prompt_hash2entry = {}    
    all_code_to_query = {}
    for entry in entries:
        entry['__cgr_ret'] = {
            "trigger": False,
            "code": "",
            "triggered_rules": [],
            "rule2details": {},
        }
        prompt = entry["task"]
        if prompt not in prompt_hash2entry:
            prompt_hash2entry[prompt] = entry
        else:
            print("Duplicate entry found for hash:", prompt)
            continue
        coder_rsp = entry['__coder_rsp']
        if '```python' not in coder_rsp:                
            continue
        coder_pfx = coder_rsp.split('```python')[1].strip()
        if '```' not in coder_pfx:
            continue
        code = coder_pfx.split('```')[0].strip()
        if len(code) == 0:
            continue
        all_code_to_query[prompt] = code

    if len(all_code_to_query) > 0:
        cgr_ret = await test_code_w_rule_details(experiments=all_code_to_query, expected_rule='any')
    else:
        cgr_ret = {}

    for prompt, ret in cgr_ret.items():
        entry = prompt_hash2entry[prompt]
        triggered_rules = ret[1]
        rule2details = ret[2]
        expected_rule = entry['rule_name']
        exact_rule_name = rule_name2exact_rule_name[expected_rule]
        trigger = exact_rule_name in triggered_rules
        code = all_code_to_query[prompt]
        entry['__cgr_ret'] = {
            "trigger": trigger,
            "code": code,
            "triggered_rules": triggered_rules,
            "rule2details": rule2details,
        }

    for entry in entries:
        fout.write(json.dumps(entry) + "\n")
        fout.flush()
        if entry['task'] in on_going:
            on_going.remove(entry['task'])

    pbar.update(len(entries))
    suffix = "Ongoing: " + str(len(on_going))
    pbar.set_postfix_str(suffix)
    pbar.refresh()

async def query_all():
    BZ = 200
    for i in range(0, len(to_process), BZ):
        while len(on_going) >= BZ * 20:
            await asyncio.sleep(1)
        current_batch = to_process[i:i+BZ]
        on_going.update([entry['task'] for entry in current_batch])
        asyncio.create_task(process_entries(current_batch))
    await asyncio.sleep(1)
    while len(on_going) > 0:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(query_all())