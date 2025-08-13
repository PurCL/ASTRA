import json
from tqdm import tqdm
import os
import glob
import random
import datasets
import uuid
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
from autogen_core import (
    RoutedAgent,
    MessageContext,
    default_subscription,
    message_handler,
    DefaultTopicId,
)
from .cgr_messages import (
    CgrExperimentRequest,
    CgrExperimentResultEntry,
    CgrExperimentResults,
)
from dataclasses import dataclass
import asyncio
from .cgr_helper import test_code
from utils import parse_tags


@default_subscription
class CgrAgent(RoutedAgent):

    def __init__(self, description: str):
        super().__init__(description=description)

    @message_handler
    async def handle_experiment_request(
        self,
        message: CgrExperimentRequest,
        context: MessageContext,
    ) -> None:
        code_snippets = message.code_snippets
        exact_rule_name = message.exact_rule_name
        cgr_ret = await test_code(
            experiments=code_snippets,
            expected_rule=exact_rule_name,
        )
        final_ret = {}
        for k, v in cgr_ret.items():
            final_ret[k] = CgrExperimentResultEntry(
                expected_rule=exact_rule_name,
                all_triggered_rules=v[1],
                trigger_expected_rule=v[0],
            )
        results = CgrExperimentResults(
            session_id=message.session_id,
            raw_prompt="",
            raw_rsp="",
            results=final_ret,
        )
        await self.publish_message(results, topic_id=DefaultTopicId())
