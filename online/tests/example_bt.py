from typing import List, Dict
import openai
import random
from pydantic import BaseModel

import yaml
import openai
import json

model_name = "microsoft/Phi-4-mini-instruct"
addr = "http://<host>:8001/v1"
api_key = yaml.safe_load(open("api-key.yaml"))["api_key"] 

coder_client = openai.OpenAI(base_url=addr, api_key=api_key)


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

ret = test_client(coder_client, model_name)
if not ret:
    print(f"Client {model_name} is not working, exiting.")
    exit(1)


def handle_chat_request(messages: List[Dict[str, str]], red_team_id: str) -> str:    
    # prepare the prompt
    messges_different_role = []
    for msg in messages:
        entry = {
            "role": 'user' if msg["role"] == "attacker" else "assistant",
            "content": msg["content"]
        }
        messges_different_role.append(entry)
    rsp = coder_client.chat.completions.create(
        model=model_name,
        messages=messges_different_role,
        max_tokens=900,
        temperature=0.8,
        n=1,
    )
    rsp_text = rsp.choices[0].message.content
    return rsp_text