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

from cgr_agent.cgr_helper import test_code
from .task_messages import (
    HelpfulnessCheckRequest,
    HelpfulnessResultEntry,
    HelpfulnessResults,
    HelpfulnessCheckEntry,
)
from reasoning_sampler import ReasoningSampler


@default_subscription
class HelpfulnessReviewAgent(RoutedAgent):

    def __init__(
        self,
        description: str,
        reasoning_sampler: ReasoningSampler
    ):
        super().__init__(description=description)
        self._reasoning_sampler = reasoning_sampler
        self._reasoning_judge_prompt = open(
            "agent/sec_event_composer/prompts/compliance_review.txt", "r"
        ).read()

    async def _query_reasoning_judge(self, task: str, code: str, goal: str) -> str:
        prompt = self._reasoning_judge_prompt.format(
            user_request=task,
            model_response=code,
            goal=goal,
        )
        query = [{"role": "user", "content": prompt}]
        retry_cnt = 0
        while retry_cnt < 2:
            rsp = await asyncio.to_thread(
                self._reasoning_sampler.sample_reasoning, query
            )
            if rsp is None:
                retry_cnt += 1
                continue
            parsed_rets = parse_tags(rsp.response, ["State", "Reasoning"])
            if len(parsed_rets["missing_tags"]) > 0:
                retry_cnt += 1
                continue
            reasoning = parsed_rets["Reasoning"].strip()
            safe = True if "Secure" in parsed_rets["State"].strip() else False
            return {
                "reasoning_safe": safe,
                "reasoning_traj": reasoning,
            }

        return None

    @message_handler
    async def handle_experiment_request(
        self,
        message: HelpfulnessCheckRequest,
        context: MessageContext,
    ) -> None:
        tag2entry = message.tag2entry

        tag2reasoning_tasks = {}
        for tag, entry in tag2entry.items():
            task = entry.task
            code = entry.code
            goal = entry.goal

            task = asyncio.create_task(
                self._query_reasoning_judge(task=task, code=code, goal=goal)
            )
            tag2reasoning_tasks[tag] = task

        ret_entries = {}
        for tag, task in tag2reasoning_tasks.items():
            reasoning_result = await asyncio.gather(task)
            reasoning_result = reasoning_result[0]
            if reasoning_result is None:
                continue
            reasoning_safe = reasoning_result["reasoning_safe"]
            reasoning_traj = reasoning_result["reasoning_traj"]
            ret_entries[tag] = HelpfulnessResultEntry(
                code=tag2entry[tag].code,
                reasoning_safe=reasoning_safe,
                reasoning_traj=reasoning_traj,
                type_name="HelpfulnessResultEntry",
            )

        results = HelpfulnessResults(
            session_id=message.session_id,
            raw_prompt="",
            raw_rsp="",
            results=ret_entries,
        )
        await self.publish_message(results, topic_id=DefaultTopicId())
