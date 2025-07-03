import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from botocore.config import Config
import multiprocessing
import time

MODEL_NAME_SONNET_35="us.anthropic.claude-3-5-sonnet-20241022-v2:0"

class RateLimiter:
    def __init__(self, max_calls, period, shared_list, shared_lock):
        self.max_calls = max_calls
        self.period = period
        self.call_times = shared_list
        self.lock = shared_lock
        thread_name = multiprocessing.current_process().name
        print(
            f"Rate limiter created by thread name: {thread_name}, with lock: {self.lock}, max_calls: {id(self.call_times)}, period: {period}"
        )

    def __enter__(self):
        while True:
            with self.lock:
                # print("Lock name: ", self.lock)
                thread_name = multiprocessing.current_process().name
                now = time.time()
                # self.call_times = [t for t in self.call_times if now - t < self.period]
                for t in self.call_times:
                    if now - t > self.period:
                        self.call_times.remove(t)
                if len(self.call_times) < self.max_calls:
                    self.call_times.append(now)
                    # print(f"[{thread_name}] Rate limiter: len(self.call_times) = ", len(self.call_times))
                    return
                sleep_time = self.call_times[0] + self.period - now
            if sleep_time > 0:
                # print(f"[{thread_name}] Rate limiter: sleeping for {sleep_time}")
                time.sleep(sleep_time)

    def __exit__(self, exc_type, exc_val, exc_tb):
        # print("Exiting rate limiter: len(self.call_times) = ", len(self.call_times))
        pass


def query_claude_w_rate_limiter(
    rate_limiter,
    messages,
    temperature=0.7,
    top_k=50,
    max_tokens=1600,
    system_prompt=None,
):
    with rate_limiter:
        config = Config(read_timeout=120)
        br_client = boto3.client(
            "bedrock-runtime", region_name="us-west-2", config=config
        )
        model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
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


def query_claude(
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
