from typing import Dict, List
from rt.data_modeling import (
    DefenderDO,
    VulCodeSchedulerDO,
    SecEventSchedulerDO,
    VulCodePromptDO,
    TagStatusEntry,
    SessionType,
)
from rt.prompt_utils import all_vul_code_prompts
from rt.logger import purcl_logger_adapter
from .vul_code_scheduler import VulCodeScheduler

class DefenderScheduler:

    def __init__(self, defender_id: str):
        self.defender_id = defender_id
        self._defender_do = DefenderDO()
        self._session_id2do = {}
        self._init_vul_code_scheduler()
        self._init_sec_event_scheduler()
        self._vul_code_scheduler = VulCodeScheduler(self._defender_do.vul_code_scheduler_do)

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
        pass

    def new_attack(self, session_id: str):
        if True:
        # if len(self._session_id2do) % 2 == 0:
            # new vul code session
            session_do, prompt = self._vul_code_scheduler.new_attack(session_id)
            self._session_id2do[session_id] = session_do
            self._defender_do.num_all_non_probing_sessions += 1
            return prompt
        else:
            # new sec event session
            purcl_logger_adapter.info("Not implemented yet for sec event scheduler.")
            raise NotImplementedError("Sec event scheduler not implemented yet.")

    def continue_attack(self, session_id: str, messages: List[Dict[str, str]]) -> str:
        if session_id not in self._session_id2do:
            raise ValueError(f"Session ID {session_id} not found.")

        session_do = self._session_id2do[session_id]
        if session_do.session_type == SessionType.VUL:
            return self._vul_code_scheduler.continue_attack(session_id, messages, session_do)
        else:
            purcl_logger_adapter.error("Sec event scheduler not implemented yet.")
            raise NotImplementedError("Sec event scheduler not implemented yet.")


    def finish_attack(self, session_id: str, messages: List[Dict[str, str]]):
        if session_id not in self._session_id2do:
            raise ValueError(f"Session ID {session_id} not found.")
        
        session_do = self._session_id2do[session_id]
        if session_do.session_type == SessionType.VUL:
            purcl_logger_adapter.info(f"Finishing vul code session {session_id}.")
            self._vul_code_scheduler.finish_attack(session_id, messages, session_do)
        else:
            purcl_logger_adapter.error("Sec event scheduler not implemented yet.")
            raise NotImplementedError("Sec event scheduler not implemented yet.")