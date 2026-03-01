"""Pricing Analyst agent - post-bid competitive pricing recommendations."""
from datapizza.agents import Agent

from src.prompts import PRICING_ANALYST_PROMPT as SYSTEM_PROMPT


def create_pricing_analyst(client, tools: list) -> Agent:
    """Create Pricing Analyst agent.
    
    Tools needed:
    - get_draft_menu (from game_tools.py) to know which dishes to price
    - get_actual_bids (from game_tools.py) to know ingredient costs
    - get_competitor_menu_prices (from analyst_tools.py) to see competitor pricing
    - save_suggested_prices (from game_tools.py) to communicate recommendations
    """
    return Agent(
        name="pricing_analyst",
        client=client,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
    )
