import asyncio
import glob
import json
import os
import random
import uuid
from dataclasses import dataclass
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    List,
    Mapping,
    Sequence,
    Set,
    TextIO,
    Tuple,
)

import datasets
from autogen_core import (
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    default_subscription,
    message_handler,
)
from tqdm import tqdm
from utils import parse_tags

from .task_messages import (
    CodingRequest,
    CodingResultEntry,
    CodingResult,
)
import openai


@default_subscription
class CoderAgent(RoutedAgent):
    def __init__(
        self,
        description: str,
        coding_clients: List[Tuple[openai.OpenAI, str]],
        best_practice: Dict[str, str] = None,
    ):
        super().__init__(description=description)
        self._name = "CoderAgent"
        self._coding_clients = coding_clients
        # if best_practice is None:
        #     self._best_practice = [
        #         json.loads(line)
        #         for line in open(
        #             "data_out/rules-bp-compose-processed.jsonl", "r"
        #         ).readlines()
        #     ] + [
        #         json.loads(line)
        #         for line in open(
        #             "data_out/rules-bp-compose-pr9-processed.jsonl", "r"
        #         ).readlines()
        #     ]
        #     self._best_practice = {
        #         entry["rule_name"]: entry["current_best_practice"]
        #         for entry in self._best_practice
        #     }
        # else:
        #     self._best_practice = best_practice
        self._best_practice = None

    async def _query_coder(self, task: str) -> CodingResultEntry:
        client = random.choice(self._coding_clients)
        openai_client, model_name = client

        def query_one():
            rsp = openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": task,
                    }
                ],
                max_tokens=600+ (len(task) // 5),
                temperature=0.4,
                n=1,
            )
            return rsp.choices[0].message.content

        retry_cnt = 0
        while retry_cnt < 3:
            try:
                response = await asyncio.to_thread(query_one)
                if "```python" not in response:
                    error_msg = "Cannot find python code block in response"
                else:
                    prefix = response.split("```python")[1]
                    if "```" in prefix:
                        code = prefix.split("```")[0]
                        error_msg = ""
                    else:
                        error_msg = (
                            "Code block is not complete (cannot find closing ```)"
                        )
                if len(error_msg) > 0:
                    return CodingResultEntry(
                        code="",
                        error_msg=error_msg,
                        success=False,
                    )
                else:
                    return CodingResultEntry(
                        code=code,
                        error_msg="",
                        success=True,
                    )

            except Exception as e:
                print(f"Error querying coder: {e}")
                retry_cnt += 1
                continue
        return CodingResultEntry(
            code="",
            error_msg="Failed to generate coder after 3 attempts",
            success=False,
        )

    @message_handler
    async def handle_coding_request(
        self,
        message: CodingRequest,
        context: MessageContext,
    ) -> None:
        tag2task = message.tasks
        tag2async_task = {}

        # best_practice = self._best_practice.get(exact_rule_name, None)        
        best_practice = None  # For now, we are not using best practices
        for tag, task in tag2task.items():
            if best_practice is not None:
                query_str = """
Please write code for the given coding task. Pay attention to the best practices:
<Best Practice> {bp} </Best Practice>
<Coding Task> {task} </Coding Task>
""".format(
                    bp=best_practice,
                    task=task,
                )
            else:
                query_str = task
            async_task = asyncio.create_task(self._query_coder(query_str))
            tag2async_task[tag] = async_task
        tag2coding_results = {}
        for tag, async_task in tag2async_task.items():
            coding_result = await async_task
            tag2coding_results[tag] = coding_result

        coding_result = CodingResult(
            session_id=message.session_id,
            raw_prompt="",
            raw_rsp="",
            results=tag2coding_results,
        )
        await self.publish_message(coding_result, topic_id=DefaultTopicId())
        return
