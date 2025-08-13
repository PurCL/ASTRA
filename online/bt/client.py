from typing import List, Dict, Any
import openai
import random
from pydantic import BaseModel
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from openai import OpenAI
import boto3
import yaml
import json
import re

class BTClient:
    def __init__(self, **kwargs):
        self.model_name = kwargs.get('model_name')
        self.addr = kwargs.get('addr')
        self.api_key = kwargs.get('api_key')
    
    def test_client(self) -> bool:
        pass 
    
    def handle_chat_request(self, messages: List[Dict[str, str]], red_team_id: str) -> str:
        pass    


class LocalOpenAIBTClient(BTClient):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = openai.OpenAI(base_url=self.addr, api_key=self.api_key)
    
    def test_client(self) -> bool:
        example_msg = [{"role": "user", "content": "Hello!"}]
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=example_msg,
                max_tokens=10,
                temperature=0.4,
                n=1,
            )
            rsp_text = response.choices[0].message.content
            print(f"Client {self.model_name} says: {rsp_text}")
            return True
        except Exception as e:
            print(f"Client {self.model_name} failed with error: {e}")
            return False
    

    def handle_chat_request(self, messages: List[Dict[str, str]], red_team_id: str) -> str:    
        # prepare the prompt
        messges_different_role = []
        for msg in messages:
            entry = {
                "role": 'user' if msg["role"] == "attacker" else "assistant",
                "content": msg["content"]
            }
            messges_different_role.append(entry)
        rsp = self.client.chat.completions.create(
            model=self.model_name,
            messages=messges_different_role,
            max_tokens=900,
            temperature=0.8,
            n=1,
        )
        rsp_text = rsp.choices[0].message.content
        return rsp_text

class BedrockBTClient(BTClient):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.region = kwargs.get("region")
        self.read_timeout = kwargs.get("read_timeout")
        self.client = boto3.client('bedrock-runtime', region_name=self.region, config=Config(read_timeout=self.read_timeout))
    
    
    def _construct_body(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        pass

    
    def _parse_response(self, response: Dict[str, Any]) -> str:
        pass
    
    def test_client(self) -> bool:
        example_msg = [{"role": "attacker", "content": "Hello!"}]
        entry = self._construct_body(example_msg)
        body = json.dumps(entry)
        try:
            response = self.client.invoke_model(
                modelId=self.model_name,
                contentType="application/json",
                body=body,
            )
            br_response = json.loads(response["body"].read().decode("utf-8"))
            rsp = self._parse_response(br_response)
            print(f"Client {self.model_name} says: {rsp}")
            return True
        except Exception as e:
            print(f"Client {self.model_name} failed with error: {e}")
            return False
    
    def handle_chat_request(self, messages: List[Dict[str, str]], red_team_id: str) -> str:
        body = self._construct_body(messages)
        body = json.dumps(body)
        try:
            response = self.client.invoke_model(
                modelId=self.model_name,
                contentType="application/json",
                body=body,
            )
            br_response = json.loads(response["body"].read().decode("utf-8"))
            rsp = self._parse_response(br_response)
            return rsp
        except Exception as e:
            print(f"Client {self.model_name} failed with error: {e}")
            return ""


class BedrockOpenAIBTClient(BedrockBTClient):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.max_completion_tokens = kwargs.get("max_completion_tokens")
        self.temperature = kwargs.get("temperature")
        self.reasoning_effort = kwargs.get("reasoning_effort")
    
    def _construct_body(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        messges_different_role = []
        for msg in messages:
            entry = {
                "role": 'user' if msg["role"] == "attacker" else "assistant",
                "content": msg["content"]
            }
            messges_different_role.append(entry)
        body = {
            "messages": messges_different_role,
            "max_completion_tokens": self.max_completion_tokens,
            "temperature": self.temperature,
            "reasoning_effort": self.reasoning_effort,
        }
        return body
    
    def _parse_response(self, response: Dict[str, Any]) -> str:
        rsp_text = response["choices"][0]["message"]["content"]
        pattern = r"<reasoning>(.*?)</reasoning>"
        reasoning_matches = re.findall(pattern, rsp_text, re.DOTALL)
        if reasoning_matches:
            reasoning = "\n".join(reasoning_matches)
        else:
            reasoning = ""
        # Remove all <reasoning></reasoning> blocks from the response
        rsp = re.sub(pattern, "", rsp_text, flags=re.DOTALL).strip()
        return rsp

class BedrockAnthropicBTClient(BedrockBTClient):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.max_tokens = kwargs.get("max_tokens")
        self.temperature = kwargs.get("temperature")
        self.anthropic_version = kwargs.get("anthropic_version")
        self.top_k = kwargs.get("top_k")
    
    def _construct_body(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        messges_different_role = []
        for msg in messages:
            entry = {
                "role": 'user' if msg["role"] == "attacker" else "assistant",
                "content": msg["content"]
            }
            messges_different_role.append(entry)
        body = {
            "messages": messges_different_role,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "anthropic_version": self.anthropic_version,
            "top_k": self.top_k,
        }
        return body
    
    def _parse_response(self, response: Dict[str, Any]) -> str:
        rsp_text = response["content"][0]["text"]
        return rsp_text





class BTClientFactory:
    _client_registry = {
        "microsoft/Phi-4-mini-instruct": LocalOpenAIBTClient,
        "Qwen/Qwen2.5-Coder-7B-Instruct": LocalOpenAIBTClient,
        "mistralai/Mistral-Instruct-8B": LocalOpenAIBTClient,
        "openai.gpt-oss-120b-1:0": BedrockOpenAIBTClient,
        "openai.gpt-oss-20b-1:0": BedrockOpenAIBTClient,
        "arn:aws:bedrock:us-west-2:897729136583:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0": BedrockAnthropicBTClient,
        "anthropic.claude-3-5-haiku-20241022-v1:0": BedrockAnthropicBTClient,
    }
    
    @classmethod
    def register_client(cls, client_name: str, client_class: type):
        cls._client_registry[client_name] = client_class
    
    @classmethod
    def create_client(cls, **kwargs) -> BTClient:
        client_name = kwargs.get('client_name')
        if client_name not in cls._client_registry:
            available_names = list(cls._client_registry.keys())
            raise ValueError(f"Unsupported client name: {client_name}. Available names: {available_names}")
        
        client_class = cls._client_registry[client_name]
        return client_class(**kwargs)
    
    @classmethod
    def get_available_clients(cls) -> List[str]:
        return list(cls._client_registry.keys())
    
    @classmethod
    def create_from_config(cls, config: Dict) -> BTClient:
        required_keys = ["client_name", "addr", "api_key"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required configuration key: {key}")
        
        return cls.create_client(**config)
