from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from pydantic import BaseModel


# @dataclass
class InternalMessage(BaseModel):
    session_id: str
    raw_prompt: str
    raw_rsp: str


class ExperimentResultEntry(BaseModel):
    rule_name: str
    exact_rule_name: str
    trigger_analyzer: bool
    reasoning_safe: bool
    reasoning_traj: str
    type_name: str = "ExperimentResultEntry"

class ExperimentRequest(InternalMessage):
    code_snippets: Dict[str, str]
    exact_rule_name: str
    rule_understanding: str
    dbg_time: str = ""
    type_name: str = "ExperimentRequest"


class ExperimentResults(InternalMessage):
    results: Dict[str, ExperimentResultEntry]
    type_name: str = "ExperimentResults"


class TaskGenEntry(BaseModel):
    rule_name: str
    exact_rule_name: str
    triggered_example: str
    context: str
    pl_feature: str
    task_format: str
    current_understanding_analyzer: str
    current_understanding_reasoning: str


class TaskGenTask(BaseModel):
    cases: List[TaskGenEntry]
    ignore_log: str = "IGNORE-LOG"


class InternalTaskGenTask(InternalMessage):
    one_case: TaskGenEntry
    type_name: str = "InternalTaskGenTask"


class TextualTaskReviewRequest(InternalMessage):
    tasks: Dict[str, str]
    type_name: str = "TextualTaskReviewRequest"


class TextualTaskReviewResultEntry(BaseModel):
    approval: bool
    review: str
    type_name: str = "TextualTaskReviewResultEntry"


class TextualTaskReviewResult(InternalMessage):
    results: Dict[str, TextualTaskReviewResultEntry]
    type_name: str = "TextualTaskReviewResult"


class CodingRequest(InternalMessage):
    exact_rule_name: str
    tasks: Dict[str, str]
    type_name: str = "CodeGenerationRequest"


class CodingResultEntry(BaseModel):
    success: bool
    code: str
    error_msg: str
    type_name: str = "CodeGenerationResultEntry"


class CodingResult(InternalMessage):
    results: Dict[str, CodingResultEntry]
    type_name: str = "CodeGenerationResult"


class TaskCodeReasoningResultEntry(BaseModel):
    task: str
    gen_code: str
    trigger_analyzer: bool
    reasoning_safe: bool
    reasoning_traj: str
    type_name: str = "TaskCodeReasoningResultEntry"


class TaskGenResult(InternalMessage):
    rule_name: str
    exact_rule_name: str
    ori_triggered_example: str
    # inspiration_example: str
    context: str
    pl_feature: str
    task_format: str

    current_understanding_analyzer: str
    current_understanding_reasoning: str
    current_understanding_textual: str

    bad_tasks: List[str]
    fail_to_trigger_tasks: List[str]
    succ_tasks: List[str]

    all_triggered_examples_w_reasoning: List[TaskCodeReasoningResultEntry]
    type_name: str = "TaskGenResult"


class TaskState(BaseModel):
    task: str
    textual_review: Optional[TextualTaskReviewResultEntry]
    coding_result: Optional[CodingResultEntry]
    exp_result: Optional[ExperimentResultEntry]

