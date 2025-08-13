import asyncio
import random
from typing import (
    List
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

from cgr_agent.cgr_helper import test_code
from .task_messages import (
    TextualTaskReviewResult,
    TextualTaskReviewResultEntry,
    TextualTaskReviewRequest,
    TaskGenResult,
)
from reasoning_sampler import ReasoningSampler
# from claude_utils import query_claude
from .diversity_helper import DiversityHelper, get_overlap_wording_hints


@default_subscription
class CodeGenTaskTextReviewAgent(RoutedAgent):

    def __init__(
        self,
        description: str,
        reasoning_sampler: ReasoningSampler,
        review_prompt_fname: str = "agent/composer_agent/prompts/review.txt",
        enable_diversity: bool = False,
        existing_tasks: List[str] = [],
    ):
        super().__init__(description=description)
        self._name = "TaskTextReviewAgent"
        self._task_review_prompt = open(review_prompt_fname, "r").read()
        self._enable_diversity = enable_diversity
        self._existing_tasks = existing_tasks
        self._reasoning_sampler = reasoning_sampler
        if enable_diversity:
            self._diversity_helper = DiversityHelper(n_workers=8)
        else:
            self._diversity_helper = None
        self._timeout = 60  # seconds
    
    async def _sample_reasoning_async(self, sampler, query):
        response = await asyncio.to_thread(sampler.sample_reasoning, query)
        return response

    async def _cal_diversity(self, query_task: str):
        if self._diversity_helper is None:
            raise ValueError("Diversity helper is not initialized")
        elif len(self._existing_tasks) == 0:
            return [(0, "")]
        else:
            current_len = len(self._existing_tasks)
            max_sample_len = min(300, current_len)
            if current_len > max_sample_len:
                current_existing_tasks = random.sample(
                    self._existing_tasks, max_sample_len
                )
            else:
                current_existing_tasks = self._existing_tasks[:max_sample_len]
            all_bleu_scores = await asyncio.to_thread(
                self._diversity_helper.calculate_diversity,
                query_task,
                current_existing_tasks,
            )
            exp_len = len(current_existing_tasks)
            actual_len = len(all_bleu_scores)
            if exp_len != actual_len:
                print("Expected length: ", exp_len)
                print("Actual length: ", actual_len)
                assert False
            return list(zip(all_bleu_scores, current_existing_tasks))

    async def _diversity_review(self, query_task):
        similarity_scores = await self._cal_diversity(query_task)
        # sort by similarity score
        sorted_scores = sorted(similarity_scores, key=lambda x: x[0])
        # get the top 1 most similar task
        most_similar_task = sorted_scores[0][1]
        # get the similarity score
        most_similar_score = sorted_scores[0][0]
        if most_similar_score < 0.2:
            return {"task_accept": True, "task_review": ""}

        hints = get_overlap_wording_hints(query_task, most_similar_task)
        msg = """
Your task is too similar to an existing task. Rephrase your task to make it more different from the existing one.
For example, for natural language, you can paraphrase, change the order of the sentences, or change the words, etc.
For code, you can reorder two irrelevant statements, change the variable names, etc.
Here are the most overlapped n-grams you may want to consider:
{hints}
""".format(
            hints=hints
        ).strip()

        return {"task_accept": False, "task_review": msg}

    async def _query_task_review(self, task: str) -> str:
        prompt = self._task_review_prompt.format(
            task=task,
        )
        query = [{"role": "user", "content": prompt}]
        retry_cnt = 0
        while retry_cnt < 3:
            try:
                rsp = await asyncio.wait_for(
                    self._sample_reasoning_async(
                        self._reasoning_sampler, query
                    ),
                    timeout=self._timeout

                )
            except:
                print("Text review agent timeout, retrying...")
                retry_cnt += 1
                continue
            if rsp is None:
                print("Text review agent returned None, retrying...")
                retry_cnt += 1
                continue
            
            try:
                rsp_txt = rsp.response.strip()
                parsed_rets = parse_tags(rsp_txt, ["Review", "Conclusion"])
                if len(parsed_rets["missing_tags"]) > 0:
                    retry_cnt += 1
                    continue
                review = parsed_rets["Review"]
                conclusion = parsed_rets["Conclusion"]
                accept = True if "Accept" in conclusion else False
                return {
                    "task_review": review,
                    "task_accept": accept,
                }
            except Exception as e:
                print(f"Error parsing response: {e}")
                retry_cnt += 1
                continue

        return {
            "task_review": "Fail to get task review",
            "task_accept": False,
        }

    @message_handler
    async def handle_textual_task_review_request(
        self,
        message: TextualTaskReviewRequest,
        context: MessageContext,
    ) -> None:
        tag2task = message.tasks
        tag2final_review_results = {}
        if self._enable_diversity:
            tag2diversity_task = {}
            for tag, task in tag2task.items():
                async_task = asyncio.create_task(self._diversity_review(task))
                tag2diversity_task[tag] = async_task
            promising_tasks = []
            for tag, async_task in tag2diversity_task.items():
                task_review = await async_task
                if task_review is None:
                    raise ValueError("Failed to get task review")

                result_entry = TextualTaskReviewResultEntry(
                    review=task_review["task_review"],
                    approval=task_review["task_accept"],
                )
                if task_review["task_accept"]:
                    promising_tasks.append(tag)
                else:
                    tag2final_review_results[tag] = result_entry
        else:
            promising_tasks = list(tag2task.keys())

        if len(promising_tasks) == 0:
            review_result = TextualTaskReviewResult(
                session_id=message.session_id,
                results=tag2final_review_results,
                raw_prompt="",
                raw_rsp="",
            )
            await self.publish_message(review_result, topic_id=DefaultTopicId())
            return
        tag2async_task = {}
        for tag in promising_tasks:
            task = tag2task[tag]
            async_task = asyncio.create_task(self._query_task_review(task))
            tag2async_task[tag] = async_task

        tag2final_review_results = {}
        for tag, async_task in tag2async_task.items():
            task_review = await async_task
            if task_review is None:
                raise ValueError("Failed to get task review")

            result_entry = TextualTaskReviewResultEntry(
                review=task_review["task_review"],
                approval=task_review["task_accept"],
            )
            tag2final_review_results[tag] = result_entry

        review_result = TextualTaskReviewResult(
            session_id=message.session_id,
            results=tag2final_review_results,
            raw_prompt="",
            raw_rsp="",
        )
        await self.publish_message(review_result, topic_id=DefaultTopicId())
        return

    @message_handler
    async def handle_generated_tasks(
        self, message: TaskGenResult, context: MessageContext
    ) -> None:
        if self._enable_diversity:
            if len(message.succ_tasks) > 0:
                select_one = random.choice(message.succ_tasks)
                self._existing_tasks.append(select_one)
                print(
                    "In text diversity reviewer, adding new tasks to existing tasks, now total tasks: ",
                    len(self._existing_tasks),
                )
