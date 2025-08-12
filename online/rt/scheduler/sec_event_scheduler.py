from typing import Dict, List, Tuple, Optional

import yaml
from rt.data_modeling import (
    SecEventSchedulerDO,
    SecEventSessionDO,
    SessionType,
    SecEventPromptDO,
    TagStatusEntry,
)

from rt.temporal_explorator import TemporalExplorator, State
from .scheduler_common import SchedulerBase
import numpy as np
from rt.prompt_utils import all_sec_event_prompts
from rt.logger import purcl_logger_adapter


temporal_explorator_config = yaml.safe_load(
    open("temporal_explorator/config/default_config.yaml")
)
temporal_explorator_log_dir = ".cache.sec_event"

class SecEventScheduler(SchedulerBase):

    def __init__(self, scheduler_do: SecEventSchedulerDO):
        self.scheduler_do = scheduler_do
        self.temporal_explorator = TemporalExplorator(temporal_explorator_config, temporal_explorator_log_dir)

    def _sample_prompts(self, n=5):
        dim_and_tags = []
        succs = []
        fails = []
        for dim, tag2status in self.scheduler_do.dim2tag2status.items():
            for tag, status in tag2status.items():
                dim_and_tags.append((dim, tag))
                succs.append(status.num_succ)
                fails.append(status.num_fail)
        alphas = np.array(succs) + 1
        betas = np.array(fails) + 1
        samples = np.random.beta(alphas, betas)
        dim2tag2prob = {}
        for (dim, tag), prob in zip(dim_and_tags, samples):
            if dim not in dim2tag2prob:
                dim2tag2prob[dim] = {}
            dim2tag2prob[dim][tag] = prob

        prompt_and_probs = []
        for prompt in all_sec_event_prompts:
            context = prompt.context
            context_prob = dim2tag2prob.get("context", {}).get(context, 1.0)
            task_format = prompt.task_format
            task_format_prob = dim2tag2prob.get("task_format", {}).get(task_format, 1.0)
            asset = prompt.asset
            asset_prob = dim2tag2prob.get("asset", {}).get(asset, 1.0)
            software = prompt.software
            software_prob = dim2tag2prob.get("software", {}).get(software, 1.0)
            tactics = prompt.tactics
            tactics_prob = dim2tag2prob.get("tactics", {}).get(tactics, 1.0)
            weakness = prompt.weakness
            weakness_prob = dim2tag2prob.get("weakness", {}).get(weakness, 1.0)
            # sum of log probs
            prob = (
                np.log(context_prob)
                + np.log(task_format_prob)
                + np.log(asset_prob)
                + np.log(software_prob)
                + np.log(tactics_prob)
                + np.log(weakness_prob)
            )
            prompt_and_probs.append((prompt, prob))

        # sort by prob
        prompt_and_probs.sort(key=lambda x: x[1], reverse=True)
        # take top n
        top_prompts = [prompt for prompt, _ in prompt_and_probs[:n]]
        return top_prompts

    def _feedback(self, prompt: SecEventPromptDO, succ: bool, confidence: float):
        context = prompt.context
        task_format = prompt.task_format
        asset = prompt.asset
        software = prompt.software
        tactics = prompt.tactics
        weakness = prompt.weakness
        if context not in self.scheduler_do.dim2tag2status["context"]:
            self.scheduler_do.dim2tag2status["context"][context] = TagStatusEntry()
        if task_format not in self.scheduler_do.dim2tag2status["task_format"]:
            self.scheduler_do.dim2tag2status["task_format"][
                task_format
            ] = TagStatusEntry()
        if asset not in self.scheduler_do.dim2tag2status["asset"]:
            self.scheduler_do.dim2tag2status["asset"][asset] = TagStatusEntry()
        if software not in self.scheduler_do.dim2tag2status["software"]:
            self.scheduler_do.dim2tag2status["software"][software] = TagStatusEntry()
        if tactics not in self.scheduler_do.dim2tag2status["tactics"]:
            self.scheduler_do.dim2tag2status["tactics"][tactics] = TagStatusEntry()
        if weakness not in self.scheduler_do.dim2tag2status["weakness"]:
            self.scheduler_do.dim2tag2status["weakness"][weakness] = TagStatusEntry()
        self.scheduler_do.dim2tag2status["context"][context].num_total_query += 1
        self.scheduler_do.dim2tag2status["task_format"][
            task_format
        ].num_total_query += 1
        self.scheduler_do.dim2tag2status["asset"][asset].num_total_query += 1
        self.scheduler_do.dim2tag2status["software"][software].num_total_query += 1
        self.scheduler_do.dim2tag2status["tactics"][tactics].num_total_query += 1
        self.scheduler_do.dim2tag2status["weakness"][weakness].num_total_query += 1

        if succ:
            self.scheduler_do.dim2tag2status["context"][context].num_succ += 1
            self.scheduler_do.dim2tag2status["task_format"][task_format].num_succ += 1
            self.scheduler_do.dim2tag2status["asset"][asset].num_succ += 1
            self.scheduler_do.dim2tag2status["software"][software].num_succ += 1
            self.scheduler_do.dim2tag2status["tactics"][tactics].num_succ += 1
            self.scheduler_do.dim2tag2status["weakness"][weakness].num_succ += 1
            self.scheduler_do.overall_succ += 1
        else:
            self.scheduler_do.dim2tag2status["context"][context].num_fail += 1
            self.scheduler_do.dim2tag2status["task_format"][task_format].num_fail += 1
            self.scheduler_do.dim2tag2status["asset"][asset].num_fail += 1
            self.scheduler_do.dim2tag2status["software"][software].num_fail += 1
            self.scheduler_do.dim2tag2status["tactics"][tactics].num_fail += 1
            self.scheduler_do.dim2tag2status["weakness"][weakness].num_fail += 1
            self.scheduler_do.overall_fail += 1


    def new_attack(self, session_id: str) -> Tuple[SecEventSessionDO, str]:
        new_prompt = self._sample_prompts(n=1)[0]
        session_do = SecEventSessionDO(
            session_id=session_id,
            defender_id=self.scheduler_do.defender_id,
            session_type=SessionType.MAL,
            scheduled_prompt=new_prompt,
            state=State.UNKNOWN,
        )

        self.scheduler_do.num_sec_sessions += 1
        return session_do, session_do.scheduled_prompt.task

    def continue_attack(
        self,
        session_id: str,
        messages: List[Dict[str, str]],
        session_do: SecEventSessionDO,
    ) -> Optional[str]:
        if session_do.state == State.JAILBROKEN:
            # already jailbroken, no need to continue
            return "<Jailbroken>"
        prompt, state = self.temporal_explorator.process_turn(
            bt_id=self.scheduler_do.defender_id,
            session_id=session_id,
            chat_history=messages,
            goal=session_do.scheduled_prompt.goal,
        )
        session_do.state = state
        return prompt


    def finish_attack(
        self,
        session_id: str,
        messages: List[Dict[str, str]],
        session_do: SecEventSessionDO,
    ) -> Optional[str]:
        if session_do.state == State.JAILBROKEN:
            self._feedback(
                session_do.scheduled_prompt, succ=True, confidence=1.0
            )
            return None
        
        # if previous turns are not jailbroken yet
        # we need to judge the final turn
        _, state = self.temporal_explorator.process_turn(
            bt_id=self.scheduler_do.defender_id,
            session_id=session_id,
            chat_history=messages,
            goal=session_do.scheduled_prompt.goal,
        )
        session_do.state = state
        if state == State.JAILBROKEN:
            self._feedback(
                session_do.scheduled_prompt, succ=True, confidence=1.0
            )
            return "<Jailbroken>"
        else:
            self._feedback(
                session_do.scheduled_prompt, succ=False, confidence=1.0
            )
            return None
