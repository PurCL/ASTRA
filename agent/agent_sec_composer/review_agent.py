from agents import function_tool,RunContextWrapper
from agents.extensions.models.litellm_model import LitellmModel
from .utils_model import get_model, get_response_text
from .context import MainAgentContext
import asyncio
import json
from datetime import datetime

def _get_current_time_str() -> str:
    return datetime.now().strftime("%Y-%m-%d-%H-%M-%S")


async def _get_review(reviewer_model: LitellmModel, request_text: str) -> str:
    reviewer_sys_prompt = open("agent/agent_sec_composer/prompts/reviewer.md", "r").read()
    query_prompt = f"<request_text>{request_text}</request_text>"
    query = [{"role": "user", "content": query_prompt}]
    return await get_response_text(reviewer_model, query, system_prompt=reviewer_sys_prompt)

@function_tool
async def review(ctx: RunContextWrapper[MainAgentContext], request_text: str) -> str:
    """
Send a generated request text to a committe of review sub-agents.
"""
    context_obj: MainAgentContext = ctx.context
    # log_fout = open(context_obj.log_fout_name, "a")
    reviewer_model_names = ["claude-sonnet-3-7", "claude-haiku-4-5", "gpt-oss-20b", "gpt-oss-120b", "qwen3coder"]

    reviewer_models = [get_model(model_name) for model_name in reviewer_model_names]
    reviews = await asyncio.gather(*[_get_review(model, request_text) for model in reviewer_models])

    model_name2review = {model_name: review for model_name, review in zip(reviewer_model_names, reviews)}
    log_out = open(context_obj.log_fout_name, "a")
    log_out.write(json.dumps({
        'timestamp': _get_current_time_str(),
        'request_text': request_text,
        'model_name2review': model_name2review,
    }) + "\n")
    log_out.flush()
    log_out.close()
    ret_str = "Here are the reviews from the reviewers:\n"
    for i, review in enumerate(reviews):
        ret_str += f"Review from Reviewer {i+1}:\n{review}\n"
    return ret_str




