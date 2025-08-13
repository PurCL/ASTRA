from typing import Dict, List
from rt.data_modeling import (
    DefenderDO,
    VulCodeSchedulerDO,
    SecEventSchedulerDO,
    VulCodePromptDO,
    TagStatusEntry,
    SessionType,
)
from rt.prompt_utils import all_vul_code_prompts, all_sec_event_prompts
from rt.logger import purcl_logger_adapter
from .vul_code_scheduler import VulCodeScheduler
from .sec_event_scheduler import SecEventScheduler

class DefenderScheduler:

    def __init__(self, defender_id: str):
        self.defender_id = defender_id
        self._defender_do = DefenderDO()
        self._session_id2do = {}
        self._init_vul_code_scheduler()
        self._init_sec_event_scheduler()
        self._vul_code_scheduler = VulCodeScheduler(self._defender_do.vul_code_scheduler_do)
        self._sec_event_scheduler = SecEventScheduler(self._defender_do.sec_event_scheduler_do)


    def _init_vul_code_scheduler(self) -> VulCodeSchedulerDO:
        vul_code_scheduler = self._defender_do.vul_code_scheduler_do
        vul_code_scheduler.defender_id = self.defender_id
        if "context" not in vul_code_scheduler.dim2tag2status:
            vul_code_scheduler.dim2tag2status["context"] = {}
        if "rule" not in vul_code_scheduler.dim2tag2status:
            vul_code_scheduler.dim2tag2status["rule"] = {}
        if "pl_feature" not in vul_code_scheduler.dim2tag2status:
            vul_code_scheduler.dim2tag2status["pl_feature"] = {}
        if "task_format" not in vul_code_scheduler.dim2tag2status:
            vul_code_scheduler.dim2tag2status["task_format"] = {}

        for prompt in all_vul_code_prompts:
            rule_name = prompt.rule_name
            context = prompt.context
            pl_feature = prompt.pl_feature
            task_format = prompt.task_format
            if context not in vul_code_scheduler.dim2tag2status["context"]:
                vul_code_scheduler.dim2tag2status["context"][context] = TagStatusEntry()
            if rule_name not in vul_code_scheduler.dim2tag2status["rule"]:
                vul_code_scheduler.dim2tag2status["rule"][rule_name] = TagStatusEntry()
            if pl_feature not in vul_code_scheduler.dim2tag2status["pl_feature"]:
                vul_code_scheduler.dim2tag2status["pl_feature"][
                    pl_feature
                ] = TagStatusEntry()
            if task_format not in vul_code_scheduler.dim2tag2status["task_format"]:
                vul_code_scheduler.dim2tag2status["task_format"][
                    task_format
                ] = TagStatusEntry()

        return vul_code_scheduler
    
    def _init_sec_event_scheduler(self) -> SecEventSchedulerDO:
        sec_event_scheduler = self._defender_do.sec_event_scheduler_do
        sec_event_scheduler.defender_id = self.defender_id
        if "context" not in sec_event_scheduler.dim2tag2status:
            sec_event_scheduler.dim2tag2status["context"] = {}
        if "pl_feature" not in sec_event_scheduler.dim2tag2status:
            sec_event_scheduler.dim2tag2status["pl_feature"] = {}
        if "task_format" not in sec_event_scheduler.dim2tag2status:
            sec_event_scheduler.dim2tag2status["task_format"] = {}
        if "asset" not in sec_event_scheduler.dim2tag2status:
            sec_event_scheduler.dim2tag2status["asset"] = {}
        if "software" not in sec_event_scheduler.dim2tag2status:
            sec_event_scheduler.dim2tag2status["software"] = {}
        if "tactics" not in sec_event_scheduler.dim2tag2status:
            sec_event_scheduler.dim2tag2status["tactics"] = {}
        if "weakness" not in sec_event_scheduler.dim2tag2status:
            sec_event_scheduler.dim2tag2status["weakness"] = {}

        for prompt in all_sec_event_prompts:
            context = prompt.context = prompt.context
            task_format = prompt.task_format = prompt.task_format
            asset = prompt.asset = prompt.asset
            software = prompt.software = prompt.software
            tactics = prompt.tactics = prompt.tactics
            weakness = prompt.weakness
            if context not in sec_event_scheduler.dim2tag2status["context"]:
                sec_event_scheduler.dim2tag2status["context"][context] = TagStatusEntry()
            if task_format not in sec_event_scheduler.dim2tag2status["task_format"]:
                sec_event_scheduler.dim2tag2status["task_format"][task_format] = TagStatusEntry()
            if asset not in sec_event_scheduler.dim2tag2status["asset"]:
                sec_event_scheduler.dim2tag2status["asset"][asset] = TagStatusEntry()
            if software not in sec_event_scheduler.dim2tag2status["software"]:
                sec_event_scheduler.dim2tag2status["software"][software] = TagStatusEntry()
            if tactics not in sec_event_scheduler.dim2tag2status["tactics"]:
                sec_event_scheduler.dim2tag2status["tactics"][tactics] = TagStatusEntry()
            if weakness not in sec_event_scheduler.dim2tag2status["weakness"]:
                sec_event_scheduler.dim2tag2status["weakness"][weakness] = TagStatusEntry()


    def new_attack(self, session_id: str):
        # if False:
        # if True:
        if len(self._session_id2do) % 2 == 0:
            # new vul code session
            session_do, prompt = self._vul_code_scheduler.new_attack(session_id)
            self._session_id2do[session_id] = session_do
            self._defender_do.num_all_non_probing_sessions += 1
            return prompt
        else:
            session_do, prompt = self._sec_event_scheduler.new_attack(session_id)
            self._session_id2do[session_id] = session_do
            self._defender_do.num_all_non_probing_sessions += 1
            return prompt

    def continue_attack(self, session_id: str, messages: List[Dict[str, str]]) -> str:
        if session_id not in self._session_id2do:
            raise ValueError(f"Session ID {session_id} not found.")

        session_do = self._session_id2do[session_id]
        if session_do.session_type == SessionType.VUL:
            return self._vul_code_scheduler.continue_attack(session_id, messages, session_do)
        else:
            return self._sec_event_scheduler.continue_attack(session_id, messages, session_do)


    def finish_attack(self, session_id: str, messages: List[Dict[str, str]]):
        if session_id not in self._session_id2do:
            raise ValueError(f"Session ID {session_id} not found.")
        
        session_do = self._session_id2do[session_id]
        if session_do.session_type == SessionType.VUL:
            purcl_logger_adapter.info(f"Finishing vul code session {session_id}.")
            self._vul_code_scheduler.finish_attack(session_id, messages, session_do)
        else:
            return self._sec_event_scheduler.finish_attack(session_id, messages, session_do)