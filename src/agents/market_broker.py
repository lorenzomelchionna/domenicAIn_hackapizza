"""Market Broker agent - inter-restaurant trading."""
from datapizza.agents import Agent

from src.prompts import MARKET_BROKER_PROMPT as SYSTEM_PROMPT


def create_market_broker(client, tools: list) -> Agent:
    """Create Market Broker agent. Tools: create_market_entry, execute_transaction, delete_market_entry."""
    return Agent(
        name="market_broker",
        client=client,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
    )
