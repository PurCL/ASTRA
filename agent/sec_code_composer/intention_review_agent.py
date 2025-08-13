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
from .task_messages import ExperimentRequest, ExperimentResultEntry, ExperimentResults
from reasoning_sampler import ReasoningSampler


@default_subscription
class IntentionReviewAgent(RoutedAgent):

    def __init__(
        self,
        description: str,
        reasoning_sampler: ReasoningSampler,
        rule_name2description: Dict[str, str],
    ):
        super().__init__(description=description)
        self._reasoning_sampler = reasoning_sampler
        self._reasoning_judge_prompt = open(
            "agent/sec_code_composer/prompts/intention_review.txt", "r"
        ).read()
        self._rule_name2description = rule_name2description

    async def _query_reasoning_judge(self, code: str, understanding: str) -> str:
        prompt = self._reasoning_judge_prompt.format(
            desc=understanding,
            code=code,
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
            parsed_rets = parse_tags(rsp.response, ["Summary", "Conclusion"])
            if len(parsed_rets["missing_tags"]) > 0:
                retry_cnt += 1
                continue
            conclusion = parsed_rets["Conclusion"].strip()
            safe = True if "Secure" in conclusion else False
            summary = parsed_rets["Summary"].strip()
            return {
                "reasoning_safe": safe,
                "reasoning_traj": summary,
            }

        return None

    @message_handler
    async def handle_experiment_request(
        self,
        message: ExperimentRequest,
        context: MessageContext,
    ) -> None:
        code_snippets = message.code_snippets
        exact_rule_name = message.exact_rule_name
        # rule_understanding = message.rule_understanding
        rule_desc = self._rule_name2description[exact_rule_name]
        ret = await test_code(
            experiments=code_snippets,
            expected_rule=exact_rule_name,
        )
        ret_entries = {}
        for tag, (trigger, rules) in ret.items():
            if trigger:
                ret_entries[tag] = ExperimentResultEntry(
                    rule_name=message.exact_rule_name,
                    exact_rule_name=exact_rule_name,
                    trigger_analyzer=True,
                    reasoning_safe=False,
                    reasoning_traj="",
                )
            else:
                ret_entries[tag] = ExperimentResultEntry(
                    rule_name=message.exact_rule_name,
                    exact_rule_name=exact_rule_name,
                    trigger_analyzer=False,
                    reasoning_safe=False,
                    reasoning_traj="",
                )

        tag2reasoning_tasks = {}
        for tag, entry in ret_entries.items():
            if entry.trigger_analyzer:
                task = asyncio.create_task(
                    self._query_reasoning_judge(
                        code=code_snippets[tag],
                        understanding=rule_desc,
                    )
                )
                tag2reasoning_tasks[tag] = task

        for tag, task in tag2reasoning_tasks.items():
            reasoning_result = await asyncio.gather(task)
            reasoning_result = reasoning_result[0]
            if reasoning_result is None:
                continue
            reasoning_safe = reasoning_result["reasoning_safe"]
            reasoning_traj = reasoning_result["reasoning_traj"]
            ret_entries[tag].reasoning_safe = reasoning_safe
            ret_entries[tag].reasoning_traj = reasoning_traj

        results = ExperimentResults(
            session_id=message.session_id,
            raw_prompt="",
            raw_rsp="",
            results=ret_entries,
        )
        await self.publish_message(results, topic_id=DefaultTopicId())
