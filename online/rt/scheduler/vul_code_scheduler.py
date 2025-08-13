from typing import Dict, List, Tuple
from rt.data_modeling import (
    VulCodeSchedulerDO,
    VulCodeSessionDO,
    SessionType,
    VulCodePromptDO,
    TagStatusEntry,
)

from .scheduler_common import SchedulerBase
import numpy as np
from rt.prompt_utils import all_vul_code_prompts
from rt.judge import VulCodeJudge
from rt.logger import purcl_logger_adapter


class VulCodeScheduler(SchedulerBase):

    def __init__(self, scheduler_do: VulCodeSchedulerDO):
        self.scheduler_do = scheduler_do

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
        for prompt in all_vul_code_prompts:
            context = prompt.context
            context_prob = dim2tag2prob["context"].get(context, 1.0)
            rule = prompt.rule_name
            rule_prob = dim2tag2prob["rule"].get(rule, 1.0)
            pl_feature = prompt.pl_feature
            pl_feature_prob = dim2tag2prob["pl_feature"].get(pl_feature, 1.0)
            task_format = prompt.task_format
            task_format_prob = dim2tag2prob["task_format"].get(task_format, 1.0)
            # sum of log probs
            prob = (
                np.log(context_prob)
                + np.log(rule_prob)
                + np.log(pl_feature_prob)
                + np.log(task_format_prob)
            )
            prompt_and_probs.append((prompt, prob))

        # sort by prob
        prompt_and_probs.sort(key=lambda x: x[1], reverse=True)
        # take top n
        top_prompts = [prompt for prompt, _ in prompt_and_probs[:n]]
        return top_prompts

    def _feedback(self, prompt: VulCodePromptDO, succ: bool, confidence: float):
        context = prompt.context
        rule = prompt.rule_name
        pl_feature = prompt.pl_feature
        task_format = prompt.task_format
        if context not in self.scheduler_do.dim2tag2status["context"]:
            self.scheduler_do.dim2tag2status["context"][context] = TagStatusEntry()
        if rule not in self.scheduler_do.dim2tag2status["rule"]:
            self.scheduler_do.dim2tag2status["rule"][rule] = TagStatusEntry()
        if pl_feature not in self.scheduler_do.dim2tag2status["pl_feature"]:
            self.scheduler_do.dim2tag2status["pl_feature"][pl_feature] = TagStatusEntry()
        if task_format not in self.scheduler_do.dim2tag2status["task_format"]:
            self.scheduler_do.dim2tag2status["task_format"][task_format] = TagStatusEntry()
        self.scheduler_do.dim2tag2status["context"][context].num_total_query += 1
        self.scheduler_do.dim2tag2status["rule"][rule].num_total_query += 1
        self.scheduler_do.dim2tag2status["pl_feature"][pl_feature].num_total_query += 1
        self.scheduler_do.dim2tag2status["task_format"][task_format].num_total_query += 1
        if succ:
            self.scheduler_do.dim2tag2status["context"][context].num_succ += 1
            self.scheduler_do.dim2tag2status["rule"][rule].num_succ += 1
            self.scheduler_do.dim2tag2status["pl_feature"][pl_feature].num_succ += 1
            self.scheduler_do.dim2tag2status["task_format"][task_format].num_succ += 1
            self.scheduler_do.overall_succ += 1
        else:
            self.scheduler_do.dim2tag2status["context"][context].num_fail += 1
            self.scheduler_do.dim2tag2status["rule"][rule].num_fail += 1
            self.scheduler_do.dim2tag2status["pl_feature"][pl_feature].num_fail += 1
            self.scheduler_do.dim2tag2status["task_format"][task_format].num_fail += 1
            self.scheduler_do.overall_fail += 1


    def new_attack(self, session_id: str) -> Tuple[VulCodeSessionDO, str]:
        new_prompts = self._sample_prompts(n=5)
        session_do = VulCodeSessionDO(
            session_id=session_id,
            defender_id=self.scheduler_do.defender_id,
            session_type=SessionType.VUL,
            scheduled_prompts=new_prompts,
        )
        self.scheduler_do.num_vul_sessions += 1
        return session_do, session_do.scheduled_prompts[0].task

    def _judge_last_turn(self, prompt: VulCodePromptDO, rsp: str):
        judge = VulCodeJudge(
            prompt=prompt.task,
            judge_prompt='',
            rsp=rsp,
            rule_name=prompt.rule_name,
        )
        succ, confidence = judge.judge()
        purcl_logger_adapter.info(
            f"Judge result: {succ}, confidence: {confidence}, rule: {prompt.rule_name}"
        )
        self._feedback(prompt, succ, confidence)
        return succ, confidence

    def continue_attack(
        self,
        session_id: str,
        messages: List[Dict[str, str]],
        session_do: VulCodeSessionDO,
    ) -> str:
        last_query = messages[-2]["content"]
        PFX = 1000
        last_prompt = None
        for prompt in session_do.scheduled_prompts:
            if prompt.task[:PFX] == last_query[:PFX]:
                last_prompt = prompt
                break
        if last_prompt is None:
            purcl_logger_adapter.error(
                f"Last query '{last_query}' not found in scheduled prompts."
            )
        else:
            # judge last turn
            succ, confidence = self._judge_last_turn(last_prompt, messages[-1]["content"])
            session_do.rewards.append(confidence)
            session_do.confidences.append(confidence)            

        queried_prompts = set()
        PFX = 1000
        for msg in messages:
            if msg["role"] == "attacker":
                queried_prompts.add(msg["content"][:PFX])
        next_prompt = None
        for prompt in session_do.scheduled_prompts:
            if prompt.task[:PFX] not in queried_prompts:
                next_prompt = prompt
                break
        if next_prompt is None:
            # randomly sample a new prompt from scheduled
            next_prompt = np.random.choice(session_do.scheduled_prompts)
        # return the next prompt as a string
        return next_prompt.task

    def finish_attack(
        self,
        session_id: str,
        messages: List[Dict[str, str]],
        session_do: VulCodeSessionDO,
    ) -> str:
        last_query = messages[-2]["content"]
        PFX = 1000
        last_prompt = None
        for prompt in session_do.scheduled_prompts:
            if prompt.task[:PFX] == last_query[:PFX]:
                last_prompt = prompt
                break
        if last_prompt is None:
            purcl_logger_adapter.error(
                f"Last query '{last_query}' not found in scheduled prompts."
            )
        else:
            # judge last turn
            succ, confidence = self._judge_last_turn(last_prompt, messages[-1]["content"])
            session_do.rewards.append(confidence)
            session_do.confidences.append(confidence)
