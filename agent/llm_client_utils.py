from tqdm import tqdm
import yaml
import openai
from reasoning_sampler import LocalOAIClientSampler



config = yaml.safe_load(open("resources/coder-config.yaml"))



coder_clients = []
for coder_abbr, entry in config.items():
    if coder_abbr not in ['phi4m', 'mistral', 'clm-7b', 'llama3-1b', 'qwen2.5coder-0.5b']:
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
for client, model_name in tqdm(coder_clients, desc="Testing coder clients..."):
    ret = test_client(client, model_name)
    if ret:
        working_coders.append((client, model_name))
    else:
        print(f"Client {model_name} is not working, removing it from the list.")


def get_sampler(sampler_name):
    if sampler_name != 'qwen3-coder':
        raise ValueError(f"Unknown sampler: {sampler_name}")
    
    clients = []
    entry = config['qwen3-coder']
    model_name = entry["model_name"]
    for info in entry["apis"]:
        addr = info["addr"]
        api_key = info["api_key"]
        client = openai.OpenAI(base_url=addr, api_key=api_key)
        clients.append((client, model_name))
    working_clients = []
    for client, model_name in clients:
        ret = test_client(client, model_name)
        if ret:
            working_clients.append((client, model_name))
        else:
            print(f"Client {model_name} is not working, removing it from the list.")
    
    sampler = LocalOAIClientSampler(
        oai_client_models=working_clients,
        sampler_name=sampler_name,
    )
    return sampler

    