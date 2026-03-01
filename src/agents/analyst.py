"""Analyst agent - market intelligence and bid recommendations."""
from datapizza.agents import Agent

from src.prompts import ANALYST_PROMPT as SYSTEM_PROMPT


def create_analyst(client, tools: list) -> Agent:
    """Create Analyst agent.
    
    Tools needed:
    - Market intelligence tools (from analyst_tools.py)
    - save_suggested_bids (from game_tools.py) to communicate recommendations
    - get_draft_menu (from game_tools.py) to know which ingredients to analyze
    """
    return Agent(
        name="analyst",
        client=client,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
    )
