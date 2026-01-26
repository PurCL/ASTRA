from __future__ import annotations

import asyncio
from agents import Agent, Runner, function_tool
from agents.extensions.models.litellm_model import LitellmModel


@function_tool
def add(a: int, b: int) -> int:
    return a + b


async def main():

    agent = Agent(
        name="Calculator",
        instructions="""
Use the add tool for arithmetic. Provide your reasoning before call a tool.
You need to make a guess before you using a tool to validate your results.
After seeing the tool's result, reply just the final number.
""".strip(),
        model=model,
        tools=[add],
    )

    result = await Runner.run(agent, "What is 7 + 5?")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
