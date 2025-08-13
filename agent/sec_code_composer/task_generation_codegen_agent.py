import asyncio
import re
import uuid
from dataclasses import dataclass
from typing import (
    Dict,
    List,
    Set,
    Tuple,
)

from autogen_core import (
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    default_subscription,
    message_handler,
)
from tqdm import tqdm
from utils import parse_tags

from .task_messages import (
    ExperimentRequest,
    ExperimentResultEntry,
    ExperimentResults,
)
from reasoning_sampler import ReasoningSampler
from .task_messages import (
    CodingRequest,
    CodingResult,
    CodingResultEntry,
    InternalTaskGenTask,
    TaskCodeReasoningResultEntry,
    TaskGenResult,
    TaskGenTask,
    TaskState,
    TextualTaskReviewRequest,
    TextualTaskReviewResult,
    TextualTaskReviewResultEntry,
)


@dataclass
class TaskDispatchConfigure:
    parallel_batch_size: int = 10
    samples_per_question: int = 1
    # num_sampler: int = 2


@default_subscription
class TaskComposingDispatchAgent(RoutedAgent):

    def __init__(self, description: str, config: TaskDispatchConfigure):
        super().__init__(description)
        self._name = "TaskDispatchAgent"
        self._config = config
        self._live_session_ids: dict[str, int] = {}
        self._finished_session_ids: Set[str] = set()
        # self._overall_pbar = tqdm(total=self._config.num_targeted_instructions)
        self._overall_pbar = None
        self._succ = 0
        self._aborted = 0

    @message_handler
    async def handle_initial_vul_code_reasoning_task(
        self, message: TaskGenTask, context: MessageContext
    ) -> None:
        if self._overall_pbar is None:
            self._overall_pbar = tqdm(
                total=len(message.cases) * self._config.samples_per_question
            )
        else:
            self._overall_pbar.total += len(message.cases) * self._config.samples_per_question
            # current progress
            self._overall_pbar.refresh()
        for case in message.cases:
            for _ in range(self._config.samples_per_question):
                while len(self._live_session_ids) >= self._config.parallel_batch_size:
                    await asyncio.sleep(1)

                session_id = str(uuid.uuid4())
                self._live_session_ids[session_id] = 1

                one_internal_task = InternalTaskGenTask(
                    session_id=session_id,
                    one_case=case,
                    raw_prompt="",
                    raw_rsp="",
                )
                await self.publish_message(one_internal_task, topic_id=DefaultTopicId())

    def _update_one_session(self, session_id):
        self._overall_pbar.update(1)
        del self._live_session_ids[session_id]
        # self._live_session_ids[session_id] -= 1
        # if self._live_session_ids[session_id] == 0:
        #     del self._live_session_ids[session_id]
        self._finished_session_ids.add(session_id)
        # update pbar status
        stats = "on going: %d, finished: %d" % (
            len(self._live_session_ids),
            len(self._finished_session_ids),
        )
        self._overall_pbar.set_postfix_str(stats)

    # @message_handler
    # async def handle_vul_code_reasoning_result(
    #     self, message: VulCodeReasoningResult, context: MessageContext
    # ) -> None:
    #     if not message.has_vul:
    #         self._succ += 1
    #         self._update_one_session(message.session_id)
    #         return

    @message_handler
    async def handle_exploring_result(
        self, message: TaskGenResult, context: MessageContext
    ) -> None:
        self._succ += 1
        self._update_one_session(message.session_id)
        return


@dataclass
class TaskGenMemory:
    # task info
    rule_name: str
    exact_rule_name: str
    ori_triggered_example: str
    # inspiration_example: str
    context: str
    pl_feature: str
    task_format: str

    initial_understanding_analyzer: str
    initial_understanding_reasoning: str

    # task state
    full_msg_history: List[Dict[str, str]]
    current_understanding_analyzer: str
    current_understanding_reasoning: str
    current_understanding_textual: str
    last_queried_experiments: Dict[str, TaskState]
    # data
    bad_tasks: List[str]
    fail_to_trigger_tasks: List[str]
    succ_tasks: List[str]
    all_triggered_examples_w_reasoning: List[Tuple[str, str, bool]]


@default_subscription
class CodeGenTaskComposingAgent(RoutedAgent):

    def __init__(
        self,
        description: str,
        reasoning_sampler: ReasoningSampler,
        gen_prompt_fname: str = "agent/composer_agent/prompts/compose.txt",
    ):
        super().__init__(description)
        self._name = "CodeGenTaskComposingAgent"
        # self.SESSION_ID_SEPARATOR = "##REASONING-AGENT##"
        self._reasoning_sampler = reasoning_sampler
        self._session_history: Dict[str, TaskGenMemory] = {}
        self._first_prompt = (
            open(
                gen_prompt_fname,
                "r",
            )
            .read()
            .strip()
        )
        self._inspiration_template = (
            open(
                "agent/sec_code_composer/prompts/compose_inspiration_template.txt", "r"
            )
            .read()
            .strip()
        )
        self._timeout = 240

    async def _sample_reasoning_async(self, sampler, query):
        response = await asyncio.to_thread(
            sampler.sample_reasoning, query, max_tokens_answer=4096
        )
        return response

    def _parse_tasks(self, generated_tasks):
        tag_begin_pattern = re.compile(r"<(Task\w+)>")
        tag2text = {}
        all_possible_begins = tag_begin_pattern.findall(generated_tasks)
        for tag in all_possible_begins:
            tag_begin = f"<{tag}>"
            tag_end = f"</{tag}>"
            start = generated_tasks.find(tag_begin)
            end = generated_tasks.find(tag_end)
            if start != -1 and end != -1:
                text = generated_tasks[start + len(tag_begin) : end]
                tag2text[tag] = text.strip()
        return tag2text

    def _parse_response(self, response_text, mem_entry):
        if "</Generation>" not in response_text:
            # add missing tag for smaller composers
            response_text += "</Generation>"
        parsed_tags = parse_tags(
            response_text,
            ["Thoughts-Analyzer", "Thoughts-Task", "Thoughts-User", "Generation"],
        )
        # if len(parsed_tags["missing_tags"]) > 0:
        #     return None

        if "Generation" not in parsed_tags:
            return None
        tag2task = self._parse_tasks(parsed_tags["Generation"].strip())
        if len(tag2task) == 0:
            return None

        if "Thoughts-Analyzer" in parsed_tags:
            current_understanding_analyzer = parsed_tags["Thoughts-Analyzer"].strip()
            mem_entry.current_understanding_analyzer = current_understanding_analyzer
        if "Thoughts-Task" in parsed_tags:
            current_understanding_textual = parsed_tags["Thoughts-Task"].strip()
            mem_entry.current_understanding_textual = current_understanding_textual

        if "Thoughts-User" in parsed_tags:
            current_understanding_reasoning = parsed_tags["Thoughts-User"].strip()
            mem_entry.current_understanding_reasoning = current_understanding_reasoning

        last_queried_experiments = {}
        for tag, task in tag2task.items():
            task_state = TaskState(
                task=task, textual_review=None, coding_result=None, exp_result=None
            )
            last_queried_experiments[tag] = task_state
        mem_entry.last_queried_experiments = last_queried_experiments
        return {
            "tag2task": tag2task,
        }

    def _gen_inspiration_string(self, context, pl_feature, task_format, rule_name) -> str:
        return self._inspiration_template.format(
            rule_name=rule_name,
            context=context,
            pl_feature=pl_feature,
            task_format=task_format,
        )

    @message_handler
    async def handle_codegen_composing_task(
        self, message: InternalTaskGenTask, context: MessageContext
    ) -> None:
        session_id = message.session_id
        one_case = message.one_case
        rule_name = one_case.rule_name
        exact_rule_name = one_case.exact_rule_name
        triggered_example = one_case.triggered_example
        context = one_case.context
        pl_feature = one_case.pl_feature
        task_format = one_case.task_format
        current_understanding_analyzer = one_case.current_understanding_analyzer
        current_understanding_reasoning = one_case.current_understanding_reasoning

        self._session_history[session_id] = TaskGenMemory(
            # task info
            rule_name=rule_name,
            exact_rule_name=exact_rule_name,
            ori_triggered_example=triggered_example,
            # inspiration_example=inspiration_example,
            context=context,
            pl_feature=pl_feature,
            task_format=task_format,
            initial_understanding_analyzer=current_understanding_analyzer,
            initial_understanding_reasoning=current_understanding_reasoning,
            # task state
            full_msg_history=[],
            current_understanding_analyzer=current_understanding_analyzer,
            current_understanding_reasoning=current_understanding_reasoning,
            current_understanding_textual="",
            last_queried_experiments={},
            # data
            bad_tasks=[],
            fail_to_trigger_tasks=[],
            succ_tasks=[],
            all_triggered_examples_w_reasoning=[],
        )

        task_gen_memory = self._session_history[session_id]

        understanding_str = """
<Analyzer>
%s
</Analyzer>
<User>
%s
</User>
        """ % (
            task_gen_memory.current_understanding_analyzer,
            task_gen_memory.current_understanding_reasoning,
        )

        inspiration_string = self._gen_inspiration_string(
            context=task_gen_memory.context,
            pl_feature=task_gen_memory.pl_feature,
            task_format=task_gen_memory.task_format,
            rule_name=task_gen_memory.rule_name,
        )

        prompt = self._first_prompt.format(
            understanding=understanding_str,
            code_snippets=triggered_example,
            inspiration=inspiration_string,
        )

        query = [{"role": "user", "content": prompt}]

        retry_cnt = 0
        success = False
        while retry_cnt < 2:
            try:
                rsp = await asyncio.wait_for(
                    self._sample_reasoning_async(self._reasoning_sampler, query),
                    timeout=self._timeout,
                )
            except:
                print("Timeout")
                rsp = None
            if rsp is None:
                retry_cnt += 1
                continue
            rsp_text = rsp.response
            parsed_rets = self._parse_response(rsp_text, task_gen_memory)
            if parsed_rets is None:
                retry_cnt += 1
                continue
            success = True
            break
        if not success:
            error_msg = TaskGenResult(
                session_id=session_id,
                raw_prompt=prompt,
                raw_rsp=(
                    "ERROR: No reasoning result"
                    if rsp is None
                    else "ERROR: Error in parsing rsp: %s" % rsp_text
                ),
                # task info
                rule_name=rule_name,
                exact_rule_name=exact_rule_name,
                ori_triggered_example=triggered_example,
                # inspiration_example=inspiration_example,
                context=context,
                pl_feature=pl_feature,
                task_format=task_format,
                current_understanding_analyzer=task_gen_memory.current_understanding_analyzer,
                current_understanding_reasoning=task_gen_memory.current_understanding_reasoning,
                current_understanding_textual=task_gen_memory.current_understanding_textual,
                # data
                bad_tasks=task_gen_memory.bad_tasks,
                fail_to_trigger_tasks=task_gen_memory.fail_to_trigger_tasks,
                succ_tasks=task_gen_memory.succ_tasks,
                all_triggered_examples_w_reasoning=task_gen_memory.all_triggered_examples_w_reasoning,
            )
            await self.publish_message(error_msg, topic_id=DefaultTopicId())
            return

        tag2task = parsed_rets["tag2task"]
        task_gen_memory.full_msg_history.extend(
            [
                {
                    "role": "user",
                    "content": prompt,
                },
                {
                    "role": "assistant",
                    "content": rsp_text,
                },
            ]
        )
        textual_review_request = TextualTaskReviewRequest(
            session_id=session_id,
            tasks=tag2task,
            raw_prompt=prompt,
            raw_rsp=rsp_text,
        )
        await self.publish_message(textual_review_request, topic_id=DefaultTopicId())
        return

    async def _revise_based_on_feedback(
        self, task_gen_memory: TaskGenMemory, session_id: str
    ):
        current_tag2task_states = task_gen_memory.last_queried_experiments
        feedback_str = "<Feedback>\n"
        all_success = True
        # any_success = False
        for tag, task_state in current_tag2task_states.items():
            current_feedback_str = "<For %s>\n" % tag
            if (task_state.textual_review is not None) and (
                not task_state.textual_review.approval
            ):
                current_feedback_str += "The task does not pass the textual review.\n"
                current_feedback_str += "Here are the suggestions:\n"
                current_feedback_str += task_state.textual_review.review
                all_success = False
            elif (task_state.coding_result is not None) and (
                not task_state.coding_result.success
            ):
                current_feedback_str += (
                    "The coder does not generate expected code based on the task.\n"
                )
                current_feedback_str += "Here are the specific problem:\n"
                current_feedback_str += task_state.coding_result.error_msg
                all_success = False
            elif task_state.exp_result is not None:
                current_feedback_str += "Here is the generated code:\n"
                current_feedback_str += (
                    "<Code>\n```python\n%s\n```\n</Code>"
                    % task_state.coding_result.code
                )
                if not task_state.exp_result.trigger_analyzer:
                    current_feedback_str += (
                        "The generated code does not trigger the static analyzer.\n"
                    )
                    all_success = False
                elif not task_state.exp_result.reasoning_safe:
                    current_feedback_str += "The generated code triggers the static analyzer, but it is not considered safe by the users.\n"
                    current_feedback_str += "Here are the reasoning:\n"
                    current_feedback_str += task_state.exp_result.reasoning_traj
                    all_success = False
                else:
                    current_feedback_str += "Success! The generated code triggers the static analyzer and is considered safe by the users.\n"
                    current_feedback_str += "Here are the reasoning:\n"
                    current_feedback_str += task_state.exp_result.reasoning_traj
                    # any_success = True

            current_feedback_str += "\n</For %s>\n" % tag
            feedback_str += current_feedback_str

        feedback_str += "\n</Feedback>"

        if all_success or len(task_gen_memory.succ_tasks) > 1:
            success_msg = TaskGenResult(
                session_id=session_id,
                raw_prompt="",
                raw_rsp="",
                # task info
                rule_name=task_gen_memory.rule_name,
                exact_rule_name=task_gen_memory.exact_rule_name,
                ori_triggered_example=task_gen_memory.ori_triggered_example,
                # inspiration_example=task_gen_memory.inspiration_example,
                context=task_gen_memory.context,
                pl_feature=task_gen_memory.pl_feature,
                task_format=task_gen_memory.task_format,
                current_understanding_analyzer=task_gen_memory.current_understanding_analyzer,
                current_understanding_reasoning=task_gen_memory.current_understanding_reasoning,
                current_understanding_textual=task_gen_memory.current_understanding_textual,
                # data
                bad_tasks=task_gen_memory.bad_tasks,
                fail_to_trigger_tasks=task_gen_memory.fail_to_trigger_tasks,
                succ_tasks=task_gen_memory.succ_tasks,
                all_triggered_examples_w_reasoning=task_gen_memory.all_triggered_examples_w_reasoning,
            )
            await self.publish_message(success_msg, topic_id=DefaultTopicId())
            return
        elif len(task_gen_memory.full_msg_history) > 2 * 10 or len(task_gen_memory.fail_to_trigger_tasks) > 20:
            # give up
            error_msg = TaskGenResult(
                session_id=session_id,
                raw_prompt="",
                raw_rsp=("ERROR: Too many rounds, giving up"),
                # task info
                rule_name=task_gen_memory.rule_name,
                exact_rule_name=task_gen_memory.exact_rule_name,
                ori_triggered_example=task_gen_memory.ori_triggered_example,
                # inspiration_example=task_gen_memory.inspiration_example,
                context=task_gen_memory.context,
                pl_feature=task_gen_memory.pl_feature,
                task_format=task_gen_memory.task_format,
                current_understanding_analyzer=task_gen_memory.current_understanding_analyzer,
                current_understanding_reasoning=task_gen_memory.current_understanding_reasoning,
                current_understanding_textual=task_gen_memory.current_understanding_textual,
                # data
                bad_tasks=task_gen_memory.bad_tasks,
                fail_to_trigger_tasks=task_gen_memory.fail_to_trigger_tasks,
                succ_tasks=task_gen_memory.succ_tasks,
                all_triggered_examples_w_reasoning=task_gen_memory.all_triggered_examples_w_reasoning,
            )
            await self.publish_message(error_msg, topic_id=DefaultTopicId())
            return

        if len(task_gen_memory.full_msg_history) > 4:
            prev_msg = task_gen_memory.full_msg_history[0]
            prev_msg_suffix = task_gen_memory.full_msg_history[-3:]
            msg_history = [prev_msg] + prev_msg_suffix
        else:
            msg_history = task_gen_memory.full_msg_history
        query = msg_history + [
            {
                "role": "user",
                "content": feedback_str,
            },
        ]
        retry_cnt = 0
        success = False
        while retry_cnt < 2:
            try:
                rsp = await asyncio.wait_for(
                    self._sample_reasoning_async(self._reasoning_sampler, query),
                    timeout=self._timeout,
                )
            except:
                print("Timeout in revise")
                rsp = None
            # rsp = await self._sample_reasoning_async(self._reasoning_sampler, query)
            if rsp is None:
                retry_cnt += 1
                continue
            rsp_text = rsp.response
            parsed_rets = self._parse_response(rsp_text, task_gen_memory)
            if parsed_rets is None:
                retry_cnt += 1
                continue
            success = True
            break
        if not success:
            error_msg = TaskGenResult(
                session_id=session_id,
                raw_prompt="",
                raw_rsp=(
                    "ERROR: No reasoning result"
                    if rsp is None
                    else "ERROR: Error in parsing rsp: %s" % rsp_text
                ),
                # task info
                rule_name=task_gen_memory.rule_name,
                exact_rule_name=task_gen_memory.exact_rule_name,
                ori_triggered_example=task_gen_memory.ori_triggered_example,
                # inspiration_example=task_gen_memory.inspiration_example,
                context=task_gen_memory.context,
                pl_feature=task_gen_memory.pl_feature,
                task_format=task_gen_memory.task_format,
                current_understanding_analyzer=task_gen_memory.current_understanding_analyzer,
                current_understanding_reasoning=task_gen_memory.current_understanding_reasoning,
                current_understanding_textual=task_gen_memory.current_understanding_textual,
                # data
                bad_tasks=task_gen_memory.bad_tasks,
                fail_to_trigger_tasks=task_gen_memory.fail_to_trigger_tasks,
                succ_tasks=task_gen_memory.succ_tasks,
                all_triggered_examples_w_reasoning=task_gen_memory.all_triggered_examples_w_reasoning,
            )
            await self.publish_message(error_msg, topic_id=DefaultTopicId())
            return
        tag2task = parsed_rets["tag2task"]
        task_gen_memory.full_msg_history.extend(
            [
                {"role": "user", "content": feedback_str},
                {"role": "assistant", "content": rsp_text},
            ]
        )
        textual_review_request = TextualTaskReviewRequest(
            session_id=session_id,
            tasks=tag2task,
            raw_prompt=feedback_str,
            raw_rsp=rsp_text,
        )
        await self.publish_message(textual_review_request, topic_id=DefaultTopicId())
        return

    @message_handler
    async def handle_textual_task_review_result(
        self, message: TextualTaskReviewResult, context: MessageContext
    ) -> None:
        session_id = message.session_id
        task_gen_memory = self._session_history[session_id]
        textual_review_results: Dict[str, TextualTaskReviewResultEntry] = (
            message.results
        )

        promising_tasks = {}
        for tag, review in textual_review_results.items():
            task_state = task_gen_memory.last_queried_experiments[tag]
            task_state.textual_review = review
            if review.approval:
                promising_tasks[tag] = task_state.task

        if len(promising_tasks) == 0:
            await self._revise_based_on_feedback(
                task_gen_memory=task_gen_memory, session_id=session_id
            )
            return

        coding_request = CodingRequest(
            session_id=session_id,
            tasks=promising_tasks,
            exact_rule_name=task_gen_memory.exact_rule_name,
            raw_prompt="",
            raw_rsp="",
        )
        await self.publish_message(coding_request, topic_id=DefaultTopicId())

    @message_handler
    async def handle_coding_result(
        self, message: CodingResult, context: MessageContext
    ) -> None:
        session_id = message.session_id
        task_gen_memory = self._session_history[session_id]
        coding_results: Dict[str, CodingResultEntry] = message.results

        promising_tasks = {}
        for tag, coding_result in coding_results.items():
            task_state = task_gen_memory.last_queried_experiments[tag]
            task_state.coding_result = coding_result
            if coding_result.success:
                promising_tasks[tag] = coding_result.code
            else:
                task_gen_memory.bad_tasks.append(task_state.task)

        if len(promising_tasks) == 0:
            await self._revise_based_on_feedback(
                task_gen_memory=task_gen_memory, session_id=session_id
            )
            return

        experiment_request = ExperimentRequest(
            session_id=session_id,
            raw_prompt="",
            raw_rsp="",
            code_snippets=promising_tasks,
            exact_rule_name=task_gen_memory.exact_rule_name,
            rule_understanding="",
        )

        await self.publish_message(experiment_request, topic_id=DefaultTopicId())
        return

    @message_handler
    async def handle_experiment_result(
        self, message: ExperimentResults, context: MessageContext
    ) -> None:
        session_id = message.session_id
        task_gen_memory = self._session_history[session_id]
        experiment_results: Dict[str, ExperimentResultEntry] = message.results

        for tag, experiment_result in experiment_results.items():
            task_state = task_gen_memory.last_queried_experiments[tag]
            task_state.exp_result = experiment_result
            if experiment_result.trigger_analyzer:
                task_code_reasoning = TaskCodeReasoningResultEntry(
                    task=task_state.task,
                    gen_code=task_state.coding_result.code,
                    trigger_analyzer=True,
                    reasoning_safe=experiment_result.reasoning_safe,
                    reasoning_traj=experiment_result.reasoning_traj,
                )
                task_gen_memory.all_triggered_examples_w_reasoning.append(
                    task_code_reasoning
                )
                if experiment_result.reasoning_safe:
                    task_gen_memory.succ_tasks.append(task_state.task)
            else:
                task_gen_memory.fail_to_trigger_tasks.append(task_state.task)

        await self._revise_based_on_feedback(
            task_gen_memory=task_gen_memory, session_id=session_id
        )
        return
