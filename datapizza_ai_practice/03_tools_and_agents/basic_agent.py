"""Basic agent: autonomous agent with custom tools (calculator, database search).

Usage: python 03_tools_and_agents/basic_agent.py
Requires: OPENAI_API_KEY or GOOGLE_API_KEY in .env
"""
import os
from dotenv import load_dotenv

from datapizza.clients.openai import OpenAIClient
from datapizza.clients.google import GoogleClient
from datapizza.tools import tool
from datapizza.agents import Agent

load_dotenv()

# Change this value to switch provider: "google" or "openai"
PROVIDER = "openai"

SYSTEM_PROMPT = "You are a helpful assistant that can answer questions and help with tasks."

@tool
def get_weather(location : str, when : str) -> str:
    """Retreives the weather info"""
    return f"Weather in {location} on {when}: 16°C, sunny."

@tool
def calculator(expression : str) -> str:
    """Performs calculations."""
    return str(eval(expression))

@tool
def search_database(query : str) -> str:
    """Searches internal revenue database. To access the database use simple keys like q1."""
    db = {"q1": "$2.5M", "q2": "$3.1M", "employes": "47"}
    return db.get(query.lower(), "Data not found.")
    

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

# agent = Agent(
#     name="Weather Agent",
#     client=client,
#     system_prompt="You are an expert weather assistant, use tools when necessary.",
#     tools=[get_weather],
# )

# agent.run("What is the weather in Turin tomorrow?", tool_choice="required") # required_first [list of tools]

agent = Agent(
    name="Analyst Agent",
    client=client,
    system_prompt="You are a business analyst, use tools to query the database and perform calculations. conclude with a brief summary.",
    tools=[calculator, search_database],
)

response = agent.run(
    "What's our total revenue for Q1 and Q2? Calculate the growth rate."
)

print(response)
