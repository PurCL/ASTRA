from agents import function_tool, RunContextWrapper
from agents.extensions.models.litellm_model import LitellmModel
from .utils_model import get_model, get_response_text
from .context import MainAgentContext


composer_model_name = "claude-sonnet-4-5"


def _get_composer_sys_prompt() -> str:
    composer_sys_prompt = open(
        "agent/agent_sec_composer/prompts/composer.md", "r").read()
    return composer_sys_prompt.strip()


async def _compose(model: LitellmModel, history: list[dict[str, str]]) -> str:
    first_message = history[0]
    if first_message["role"] == "system":
        sys_prompt = first_message["content"]
    else:
        sys_prompt = _get_composer_sys_prompt()
    query = history[1:]
    return await get_response_text(model, query, system_prompt=sys_prompt)


@function_tool
async def compose_initial_draft(ctx: RunContextWrapper[MainAgentContext], prohibited_domain: str = None, technique_family: str = None, concrete_prohibited_instance: str = None, seed_context: str = None, difficulty_goal: str = None, format_constraints: str = None) -> str:
    """
This tool calls the composer agent to compose the initial draft of the test case.
The composer agent will reset its history and compose an initial draft of the test cases.
Then it will maintain all revision history until this tool is called again.
    """
    context_obj: MainAgentContext = ctx.context
    seed_context = f"<seed_context>{seed_context}</seed_context>" if seed_context else ""
    difficulty_goal = f"<difficulty_goal>{difficulty_goal}</difficulty_goal>" if difficulty_goal else ""
    format_constraints = f"<format_constraints>{format_constraints}</format_constraints>" if format_constraints else ""
    input_template = """
<case_brief>
  <prohibited_domain>{prohibited_domain}</prohibited_domain>
  <technique_family>{technique_family}</technique_family>
  <concrete_prohibited_instance>{concrete_prohibited_instance}</concrete_prohibited_instance>
  {seed_context}
  {difficulty_goal}
  {format_constraints}
</case_brief>
"""
    input_text = input_template.format(prohibited_domain=prohibited_domain, technique_family=technique_family, concrete_prohibited_instance=concrete_prohibited_instance,
                                       seed_context=seed_context, difficulty_goal=difficulty_goal, format_constraints=format_constraints)

    sys_prompt = _get_composer_sys_prompt()
    context_obj.composing_agent_history = []
    context_obj.composing_agent_history.extend([
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": input_text}
    ])
    rsp_txt = await _compose(get_model(composer_model_name), context_obj.composing_agent_history)
    context_obj.composing_agent_history.append(
        {"role": "assistant", "content": rsp_txt}
    )
    return rsp_txt


@function_tool
async def compose_revision(ctx: RunContextWrapper[MainAgentContext], revision_request: str) -> str:
    """
This tool calls the composer agent to compose a revision of the test case.
The composer agent will maintain its history and compose a revision of the test cases.
    """
    context_obj: MainAgentContext = ctx.context
    context_obj.composing_agent_history.append(
        {"role": "user", "content": revision_request}
    )
    rsp_txt = await _compose(get_model(composer_model_name), context_obj.composing_agent_history)
    context_obj.composing_agent_history.append(
        {"role": "assistant", "content": rsp_txt}
    )
    return rsp_txt
