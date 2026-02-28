"""Restaurant Manager orchestrator agent."""
from datapizza.agents import Agent

from src.prompts import RESTAURANT_MANAGER_PROMPT as SYSTEM_PROMPT


def create_restaurant_manager(client, sub_agents: list, tools: list) -> Agent:
    """Create the orchestrator agent. No tools; delegates via can_call."""
    agent = Agent(
        name="restaurant_manager",
        client=client,
        system_prompt=SYSTEM_PROMPT,
        stateless=False,
        tools=tools,
    )
    agent.can_call(sub_agents)
    return agent
