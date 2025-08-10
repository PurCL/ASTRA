import json
from tqdm import tqdm


data_in = [json.loads(line) for line in tqdm(open("data_out/syn_sec_event_tasks.jsonl", "r"))]

total = 0
for item in data_in:
    total += len(item['succ_tasks'])
print(len(data_in))
