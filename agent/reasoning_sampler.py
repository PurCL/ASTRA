import json
from typing import Dict, List
from botocore.config import Config

import boto3
from botocore.exceptions import BotoCoreError, ClientError
import asyncio
from dataclasses import dataclass
import openai
import yaml
import random

@dataclass
class ReasoningResult:
    response: str
    reasoning: str


class ReasoningSampler:

    def sample_reasoning(
        self, query: List[Dict], reasoning_budget, max_tokens_answer
    ) -> ReasoningResult:
        pass

    def get_sampler_id(self) -> str:
        pass


class BedrockClient:
    def __init__(self, region_name, config):
        self.client = boto3.client(
            "bedrock-runtime", region_name=region_name, config=config
        )

    def invoke_model(self, model_id, input_data, content_type="application/json"):
        try:
            response = self.client.invoke_model(
                modelId=model_id, contentType=content_type, body=input_data
            )
            return response["body"].read().decode("utf-8")
        except (BotoCoreError, ClientError) as error:
            print("Error happened calling bedrock client: %s" % str(error))
            return {"error": str(error)}


class ClaudeReasoningSampler(ReasoningSampler):

    def __init__(self):
        self.config = Config(read_timeout=240)
        self.model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
        self.br_client = BedrockClient("us-west-2", self.config)

    def get_sampler_id(self):
        return "CLAUDE-REASONING-SAMPLER"

    def sample_reasoning(
        self, query: List[Dict], reasoning_budget=8192, max_tokens_answer=8192
    ) -> ReasoningResult:
        body = json.dumps(
            {
                "messages": query,
                "max_tokens": max_tokens_answer + reasoning_budget,
                "anthropic_version": "bedrock-2023-05-31",
                # must be 1 when using thinking
                "temperature": 1,
                # must be unset when using thinking
                # "top_k": 50,
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": reasoning_budget,
                },
            }
        )
        br_response = self.br_client.invoke_model(self.model_id, body)
        if type(br_response) == dict and "error" in br_response:
            print("Error happened calling sampler: %s" % str(br_response["error"]))
            return None
        br_response = json.loads(br_response)        
        thinking_response = []
        normal_output = []
        for rsp in br_response["content"]:
            msg_type = rsp["type"]
            if "thinking" == msg_type:
                thinking_response.append(rsp["thinking"])
            elif "text" == msg_type:
                normal_output.append(rsp["text"])
            else:
                print(f"Unknown message type: {msg_type}")
                print("Message: ", rsp)

        return ReasoningResult(
            reasoning="".join(thinking_response), response="".join(normal_output)
        )


class DeepSeekReasoningSampler(ReasoningSampler):

    def __init__(self):
        self.config = Config(read_timeout=240)
        self.model_id = "us.deepseek.r1-v1:0"
        self.br_client = boto3.client(
            service_name="bedrock-runtime", config=self.config, region_name="us-west-2"
        )

    def get_sampler_id(self):
        return "DEEPSEEK-REASONING-SAMPLER"

    def sample_reasoning(
        self, query: List[Dict], reasoning_budget=8192, max_tokens_answer=8192
    ) -> ReasoningResult:
        inference_config = {
            "temperature": 1,
            "maxTokens": max_tokens_answer + reasoning_budget,
        }        
        query_w_converse_format = []
        for msg in query:
            query_w_converse_format.append(
                {"role": "user", "content": [{"text": msg["content"]}]}
            )
        rsp = None
        try:
            rsp = self.br_client.converse(
                modelId=self.model_id, messages=query_w_converse_format, inferenceConfig=inference_config
            )
            rsp_content = rsp["output"]["message"]["content"]
            txt = rsp_content[0]["text"]
            reasoning = rsp_content[1]["reasoningContent"]["reasoningText"]["text"]
            return ReasoningResult(response=txt, reasoning=reasoning)
        except Exception as error:
            print("Error happened calling bedrock: %s" % str(error))
            if rsp is not None:
                print("Response from bedrock: %s" % str(rsp))
            # print(rsp)
            return None



class LocalDeepSeekSampler(ReasoningSampler):

    def __init__(self):
        self.model_name = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"
        self.client = openai.OpenAI(
            base_url="http://<YOUR_HOST>/v1",
            api_key="<YOUR_API_KEY>"
        )

    def get_sampler_id(self):
        return "LOCAL_DEEPSEEK-REASONING-SAMPLER"

    def sample_reasoning(
        self, query: List[Dict], reasoning_budget=8192, max_tokens_answer=8192
    ) -> ReasoningResult:
        try:
            rsp = self.client.chat.completions.create(
                model=self.model_name,
                messages=query,
                max_tokens=min(8192, max_tokens_answer + reasoning_budget),
                temperature=1,
            )
            rsp_text = rsp.choices[0].message.content
            if '</think>' not in rsp_text:
                print("Error happened calling local deepseek: no think tags")
                return None
            reasoning = rsp_text.split('</think>')[0]
            response = rsp_text.split('</think>')[1].strip()
            return ReasoningResult(response=response, reasoning=reasoning)
        except Exception as error:
            print("Error happened calling local deepseek: %s" % str(error))
            return None


class LocalQwen3Sampler(ReasoningSampler):

    def __init__(self):
        self.model_name = "Qwen/Qwen3-30B-A3B"
        config = yaml.safe_load(open('resources/coder-config.yaml', 'r'))
        model = config['qwen3']
        self.clients = []
        for info in model["apis"]:
            addr = info["addr"]
            api_key = info["api_key"]
            client = openai.OpenAI(base_url=addr, api_key=api_key)
            self.clients.append(client)


    def get_sampler_id(self):
        return "LOCAL_QWEN3-REASONING-SAMPLER"

    def sample_reasoning(
        self, query: List[Dict], reasoning_budget=8192, max_tokens_answer=8192
    ) -> ReasoningResult:
        try:
            current_client = random.choice(self.clients)
            rsp = current_client.chat.completions.create(
                model=self.model_name,
                messages=query,
                max_tokens=min(8192, max_tokens_answer + reasoning_budget),
                temperature=0.6,
                top_p=0.95
            )
            rsp_text = rsp.choices[0].message.content
            if '</think>' not in rsp_text:
                print("Error happened calling local qwen3: no think tags")
                return None
            reasoning = rsp_text.split('</think>')[0]
            response = rsp_text.split('</think>')[1].strip()
            return ReasoningResult(response=response, reasoning=reasoning)
        except Exception as error:
            print("Error happened calling local qwen3: %s" % str(error))
            return None


def _query_claude(
    messages, model_id="anthropic.claude-3-5-haiku-20241022-v1:0", temperature=0.7, top_k=50, max_tokens=1600, system_prompt=None
):
    config = Config(read_timeout=120)
    br_client = boto3.client("bedrock-runtime", region_name="us-west-2", config=config)
    # model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    entry = {
        "messages": messages,
        "max_tokens": max_tokens,
        "anthropic_version": "bedrock-2023-05-31",
        "temperature": temperature,
        "top_k": top_k,
    }
    if system_prompt:
        entry["system"] = system_prompt
    # Need to request access to foundation models https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html
    body = json.dumps(entry)
    try:
        br_response = br_client.invoke_model(
            modelId=model_id, contentType="application/json", body=body
        )
        return json.loads(br_response["body"].read().decode("utf-8"))
    except (BotoCoreError, ClientError) as error:
        print("Error happened calling bedrock")
        print(str(error))
        return {"error": str(error)}

class HaikuSampler(ReasoningSampler):

    def __init__(self):
        self.model_id = "anthropic.claude-3-5-haiku-20241022-v1:0"
        
    def get_sampler_id(self):
        return "CLAUDE-HAIKU-SAMPLER"

    def sample_reasoning(
        self, query: List[Dict], reasoning_budget=8192, max_tokens_answer=8192
    ) -> ReasoningResult:
        rsp = _query_claude(
            messages=query,
            model_id=self.model_id,
            max_tokens=max_tokens_answer + reasoning_budget,
            temperature=0.7,
        )
        try:
            rsp_txt = rsp["content"][0]["text"]
            return ReasoningResult(
                reasoning='',
                response=rsp_txt
            )
        except Exception as error:
            print("Error happened calling sampler: %s" % str(error))
            return None
        

class SonnetSampler(ReasoningSampler):

    def __init__(self):
        self.model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        
    def get_sampler_id(self):
        return "CLAUDE-SONNET-SAMPLER"

    def sample_reasoning(
        self, query: List[Dict], reasoning_budget=8192, max_tokens_answer=8192
    ) -> ReasoningResult:
        rsp = _query_claude(
            messages=query,
            model_id=self.model_id,
            max_tokens=max_tokens_answer + reasoning_budget,
            temperature=0.7,
        )
        try:
            rsp_txt = rsp["content"][0]["text"]
            return ReasoningResult(
                reasoning='',
                response=rsp_txt
            )
        except Exception as error:
            print("Error happened calling sampler: %s" % str(error))
            return None

class LocalOAIClientSampler(ReasoningSampler):
    
    def __init__(self, oai_client_models, sampler_name):
        self.client_models = oai_client_models
        self.sampler_name = sampler_name

    def get_sampler_id(self):
        return f"LOCAL_OAI_CLIENT-SAMPLER-{self.sampler_name}"
    

    def sample_reasoning(
        self, query: List[Dict], reasoning_budget=8192, max_tokens_answer=8192
    ) -> ReasoningResult:
        try:
            current_client, model_name = random.choice(self.client_models)
            rsp = current_client.chat.completions.create(
                model=model_name,
                messages=query,
                max_tokens=min(8192, max_tokens_answer + reasoning_budget),
                temperature=1,
            )
            rsp_text = rsp.choices[0].message.content            
            return ReasoningResult(response=rsp_text, reasoning='')
        except Exception as error:
            print("Error happened calling local OAI Client: %s" % str(error))
            return None

