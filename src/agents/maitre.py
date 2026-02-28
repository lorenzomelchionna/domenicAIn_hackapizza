"""Maitre agent - customer service."""
from datapizza.agents import Agent

from src.prompts import MAITRE_PROMPT as SYSTEM_PROMPT


def create_maitre(client, tools: list) -> Agent:
    """Create Maitre agent. Tools: prepare_dish, serve_dish."""
    return Agent(
        name="maitre",
        client=client,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
    )
