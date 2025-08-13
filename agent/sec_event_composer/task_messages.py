from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from pydantic import BaseModel


# @dataclass
class InternalMessage(BaseModel):
    session_id: str
    raw_prompt: str
    raw_rsp: str


class HelpfulnessResultEntry(BaseModel):
    code: str
    reasoning_safe: bool
    reasoning_traj: str
    type_name: str = "HelpfulnessResultEntry"

class HelpfulnessCheckEntry(BaseModel):
    task: str
    code: str
    goal: str

class HelpfulnessCheckRequest(InternalMessage):
    tag2entry: Dict[str, HelpfulnessCheckEntry]    
    dbg_time: str = ""
    type_name: str = "HelpfulnessCheckRequest"


class HelpfulnessResults(InternalMessage):
    results: Dict[str, HelpfulnessResultEntry]
    type_name: str = "HelpfulnessResults"


class SecEventTaskGenEntry(BaseModel):
    context: str
    task_format: str
    asset: str
    software: str
    tactics: str
    weakness: str

class TaskGenTask(BaseModel):
    cases: List[SecEventTaskGenEntry]
    ignore_log: str = "IGNORE-LOG"


class InternalTaskGenTask(InternalMessage):
    one_case: SecEventTaskGenEntry
    type_name: str = "InternalTaskGenTask"


class IntentionReviewRequest(InternalMessage):
    tasks: Dict[str, str]
    type_name: str = "TextualTaskReviewRequest"


class IntentionReviewResultEntry(BaseModel):
    approval: bool
    review: str
    type_name: str = "TextualTaskReviewResultEntry"


class IntentionReviewResult(InternalMessage):
    results: Dict[str, IntentionReviewResultEntry]
    type_name: str = "TextualTaskReviewResult"


class CodingRequest(InternalMessage):
    tasks: Dict[str, str]
    type_name: str = "CodeGenerationRequest"


class CodingResultEntry(BaseModel):
    code: str
    error_msg: str
    success: bool
    type_name: str = "CodeGenerationResultEntry"


class CodingResult(InternalMessage):
    results: Dict[str, CodingResultEntry]
    type_name: str = "CodeGenerationResult"


class TaskCodeReasoningResultEntry(BaseModel):
    task: str
    goal: str
    gen_code: str
    reasoning_safe: bool
    reasoning_traj: str
    type_name: str = "TaskCodeReasoningResultEntry"


class TaskGenResult(InternalMessage):
    context: str
    task_format: str
    asset: str
    software: str
    tactics: str
    weakness: str

    current_understanding_coder: str
    current_understanding_reasoning: str
    current_understanding_task: str

    # tasks fail at intention check
    bad_intention_tasks: List[str]
    # tasks that coder does not generate dangerous code
    fail_to_trigger_tasks: List[str]
    succ_tasks: List[str]

    all_triggered_examples_w_reasoning: List[TaskCodeReasoningResultEntry]
    type_name: str = "TaskGenResult"


class TaskState(BaseModel):
    task: str
    goal: str
    intention_review: Optional[IntentionReviewResultEntry]
    coding_result: Optional[CodingResultEntry]
    exp_result: Optional[HelpfulnessResultEntry]
