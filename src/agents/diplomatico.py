"""Diplomatico agent - diplomacy and collaboration."""
from datapizza.agents import Agent

from src.prompts import DIPLOMATICO_PROMPT as SYSTEM_PROMPT


def create_diplomatico(client, tools: list) -> Agent:
    """Create Diplomatico agent. Tools: send_message."""
    return Agent(
        name="diplomatico",
        client=client,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
    )
