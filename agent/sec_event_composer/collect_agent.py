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
)
from autogen_core import (
    RoutedAgent,
    MessageContext,
    default_subscription,
    message_handler,
    DefaultTopicId,
)
from .task_messages import TaskGenResult
import dataclasses
import asyncio



@default_subscription
class TaskGenCollectAgent(RoutedAgent):

    def __init__(self, description: str, fout: TextIO, callback: Callable[[TaskGenResult], None]=None):        
        super().__init__(description)
        self._name = "TaskGenCollectAgent"
        self._fout = fout
        self._callback = callback

    @message_handler
    async def handle_vul_code_reasoning_result(
        self, message: TaskGenResult, context: MessageContext
    ) -> None:
        ret_dict = message.dict()
        self._fout.write(json.dumps(ret_dict) + "\n")
        self._fout.flush()
        if self._callback is not None:
            self._callback(message)
        else:
            print("No callback provided, skipping further processing.")
