import json
from pydantic import BaseModel
from rt.logger.setup import purcl_logger_adapter
from .scheduler import VulCodeSchedulerDO, SecEventSchedulerDO


class DefenderDO(BaseModel):    
    num_all_non_probing_sessions: int = 0
    vul_code_scheduler_do: VulCodeSchedulerDO = VulCodeSchedulerDO()
    sec_event_scheduler_do: SecEventSchedulerDO = SecEventSchedulerDO()

