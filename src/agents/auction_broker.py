"""Auction Broker agent - supplier procurement."""
from datapizza.agents import Agent

from src.prompts import AUCTION_BROKER_PROMPT as SYSTEM_PROMPT


def create_auction_broker(client, tools: list) -> Agent:
    """Create Auction Broker agent. Tools: closed_bid."""
    return Agent(
        name="auction_broker",
        client=client,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
    )
