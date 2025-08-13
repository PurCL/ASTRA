from pydantic import BaseModel
from typing import Dict, List, Tuple

class TagStatusEntry(BaseModel):
    num_total_query: int = 0
    num_tag_total: int = 0
    num_succ: int = 0
    num_fail: int = 0


class VulCodeSchedulerDO(BaseModel):
    defender_id: str = ""
    num_vul_sessions: int = 0
    stage: str = ""
    dim2tag2status: Dict[str, Dict[str, TagStatusEntry]] = {}
    overall_succ: int = 0
    overall_fail: int = 0


class SecEventSchedulerDO(BaseModel):
    defender_id: str = ""
    num_sec_sessions: int = 0
    stage: str = ""
    dim2tag2status: Dict[str, Dict[str, TagStatusEntry]] = {}
    overall_succ: int = 0
    overall_fail: int = 0
    