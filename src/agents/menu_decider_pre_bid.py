"""Menu Decider (Pre-Bid) agent."""
from datapizza.agents import Agent

from src.prompts import MENU_DECIDER_PRE_BID_PROMPT as SYSTEM_PROMPT


def create_menu_decider_pre_bid(client, tools: list) -> Agent:
    """Create Menu Decider Pre-Bid agent. Tools: save_menu."""
    return Agent(
        name="menu_decider_pre_bid",
        client=client,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
    )
