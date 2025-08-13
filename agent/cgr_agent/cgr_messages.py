from dataclasses import dataclass
from typing import Dict, List, Tuple
from pydantic import BaseModel

# @dataclass
class InternalMessage(BaseModel):
    session_id: str
    raw_prompt: str
    raw_rsp: str


class CgrExperimentRequest(InternalMessage):
    code_snippets: Dict[str, str]
    exact_rule_name: str
    type_name: str = "CgrExperimentRequest"

class CgrExperimentResultEntry(BaseModel):
    expected_rule: str
    all_triggered_rules: List[str]    
    trigger_expected_rule: bool
    type_name: str = "CgrExperimentResultEntry"

# @dataclass
class CgrExperimentResults(InternalMessage):
    results: Dict[str, CgrExperimentResultEntry]
    type_name: str = "CgrExperimentResults"