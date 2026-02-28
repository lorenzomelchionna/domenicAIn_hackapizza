"""Restaurant Manager orchestrator agent."""
from datapizza.agents import Agent

from src.prompts import RESTAURANT_MANAGER_PROMPT as SYSTEM_PROMPT


def create_restaurant_manager(client, sub_agents: list, tools: list) -> Agent:
    """Create the orchestrator agent. Sub-agents are wired via phase-gated tools externally."""
    agent = Agent(
        name="restaurant_manager",
        client=client,
        system_prompt=SYSTEM_PROMPT,
        stateless=False,
        tools=tools,
    )
    if sub_agents:
        agent.can_call(sub_agents)
    return agent
