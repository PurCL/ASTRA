from pydantic import BaseModel
from typing import Dict, List, Tuple

class VulCodePromptDO(BaseModel):
    task: str
    rationale: str
    rule_name: str
    exact_rule_name: str
    context: str
    pl_feature: str
    task_format: str
    ori_triggered_example: str


class SecEventPromptDO(BaseModel):
    task: str
    goal: str
    context: str
    task_format: str
    asset: str
    software: str
    tactics: str
    weakness: str
    