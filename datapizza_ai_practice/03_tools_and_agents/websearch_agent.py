"""Web-search agent: agent with built-in DuckDuckGo search tool.

Usage: python 03_tools_and_agents/websearch_agent.py
Requires: OPENAI_API_KEY or GOOGLE_API_KEY in .env
"""
import os
from dotenv import load_dotenv

from datapizza.clients.openai import OpenAIClient
from datapizza.clients.google import GoogleClient
from datapizza.tools.duckduckgo import DuckDuckGoSearchTool
from datapizza.agents import Agent

load_dotenv()

# Change this value to switch provider: "google" or "openai"
PROVIDER = "openai"

SYSTEM_PROMPT = "You are a helpful assistant that can answer questions and help with tasks."


if PROVIDER == "openai":
    client = OpenAIClient(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-5.1",
        system_prompt=SYSTEM_PROMPT,
    )
elif PROVIDER == "google":
    client = GoogleClient(
        api_key=os.getenv("GOOGLE_API_KEY"),
        model="gemini-flash-latest",
        system_prompt=SYSTEM_PROMPT,
    )
else:
    raise ValueError("Invalid PROVIDER. Use 'openai' or 'google'.")

agent = Agent(
    name="Analyst Agent",
    client=client,
    system_prompt="You are a helpful assistant. Use tools when necessary.",
    tools=[DuckDuckGoSearchTool()],
)

response = agent.run(
    "How tall is the Vesuvio?"
)

print(response)
