import yaml
from tqdm import tqdm
import json
import openai
from multiprocessing import Pool
import multiprocessing
import os

config = yaml.safe_load(open("resources/coder-config.yaml"))
fin = [
    json.loads(line)
    for line in open("data_out/syn_sec_code_tasks-phi4m-only_export.jsonl", "r").readlines()
]

fout_name = "data_out/syn_sec_code_tasks-phi4m-only_export-inference.jsonl"
if os.path.exists(fout_name):
    existing_data = [json.loads(line) for line in open(fout_name, "r")]
    fout = open(fout_name, "a")
else:
    existing_data = []
    fout = open(fout_name, "w")

seen_tasks = set()
for entry in existing_data:
    seen_tasks.add(entry["task"])

to_query = []
for entry in fin:
    task = entry["task"]
    if task not in seen_tasks:
        to_query.append(entry)



coder_clients = []
for coder_abbr, entry in config.items():
    if coder_abbr not in ["phi4m"]:
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


def query_openai(prompt):
    global my_worker_id
    my_client, model_name = working_coders[my_worker_id % len(working_coders)]
    try:
        rsp = my_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt['task']}],
            max_tokens=1024,
            temperature=0.8,
            n=1,
        )
        rsp_text = rsp.choices[0].message.content
        return {
            **prompt,
            '__coder_rsp': rsp_text,
        }
    
    except Exception as e:
        return None


worker_id = 0


def worker_init(worker_id):
    global my_worker_id
    with worker_id.get_lock():
        my_worker_id = worker_id.value
        worker_id.value += 1
    print(f"Worker {my_worker_id} started")


ctx = multiprocessing.get_context("spawn")
worker_id = ctx.Value("i", 0)
pool = multiprocessing.Pool(len(working_coders)*4, worker_init, (worker_id,))

ret = pool.imap_unordered(query_openai, to_query, chunksize=1)
for entry in tqdm(ret, total=len(to_query)):
    if entry is None:
        continue
    fout.write(json.dumps(entry) + "\n")
    fout.flush()