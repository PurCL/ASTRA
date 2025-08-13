from pydantic import BaseModel
from typing import Dict, List, Tuple
from enum import Enum
from rt.logger.setup import purcl_logger_adapter
from .prompts import SecEventPromptDO, VulCodePromptDO
from rt.temporal_explorator.models.state import State


class SessionType(Enum):
    MAL = "mal"
    VUL = "vul"
    MIX = "mix"
    SEP = "sep"

    @classmethod
    def from_str(cls, session_type_str):
        if session_type_str.lower().strip() == "mix":
            return cls.MIX
        elif session_type_str.lower().strip() == "mal":
            return cls.MAL
        elif session_type_str.lower().strip() == "vul":
            return cls.VUL
        elif session_type_str.lower().strip() == "sep":
            return cls.SEP
        else:
            purcl_logger_adapter.error(f"Unknown session type: {session_type_str}")
            return cls.MAL


class SessionDO(BaseModel):
    session_id: str
    defender_id: str
    session_type: SessionType


class VulCodeSessionDO(SessionDO):    
    scheduled_prompts: List[VulCodePromptDO]
    rewards: List[float] = []
    confidences: List[float] = []


class SecEventSessionDO(SessionDO):
    scheduled_prompt: SecEventPromptDO
    state: State
