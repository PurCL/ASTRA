from agents import Agent, Runner
from .utils_model import get_model, agent_sec_config
from .context import MainAgentContext
from .composer_agent import compose_initial_draft, compose_revision
from .review_agent import review
from pydantic import BaseModel
from typing import Optional

class MainAgentInput(BaseModel):
    problem_id: str
    prohibited_domain: str
    technique_family: str
    concrete_prohibited_instance: str
    seed_context: Optional[str] = None
    difficulty_goal: Optional[str] = None
    format_constraints: Optional[str] = None


def _get_main_agent_context(problem_id: str) -> MainAgentContext:
    import os
    log_dir = agent_sec_config.get("log_dir", "log_out_agent_sec")
    os.makedirs(log_dir, exist_ok=True)
    return MainAgentContext(
        instance_id=problem_id,
        log_fout_name=f"{log_dir}/log_agent_sec_{problem_id}.jsonl",
        composing_agent_history=[],
    )


def _get_query_prompt(input: MainAgentInput) -> str:
    seed_context = input.seed_context
    difficulty_goal = input.difficulty_goal
    format_constraints = input.format_constraints
    prohibited_domain = input.prohibited_domain
    technique_family = input.technique_family
    concrete_prohibited_instance = input.concrete_prohibited_instance
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
    return input_text.strip()

async def run_main_agent(input: MainAgentInput) -> str:
    context = _get_main_agent_context(input.problem_id)
    main_agent_sys_prompt = open("agent/agent_sec_composer/prompts/coordinator.md", "r").read()
    coordinator_model = agent_sec_config.get("coordinator_model", "claude-sonnet-4-5")
    agent = Agent[MainAgentInput](
        name="MainAgent",
        instructions=main_agent_sys_prompt,
        model=get_model(coordinator_model),
        tools=[compose_initial_draft, compose_revision, review]
    )
    query_prompt = _get_query_prompt(input)
    result = await Runner.run(agent, query_prompt, context=context, max_turns=100)
    return (result.final_output, result.to_input_list())
