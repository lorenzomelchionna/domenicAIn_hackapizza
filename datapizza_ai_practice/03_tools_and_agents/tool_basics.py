"""Tool basics: define a @tool function and invoke it via the LLM's function-calling API.

Usage: python 03_tools_and_agents/tool_basics.py
Requires: OPENAI_API_KEY or GOOGLE_API_KEY in .env
"""
import os
from dotenv import load_dotenv

from datapizza.clients.openai import OpenAIClient
from datapizza.clients.google import GoogleClient
from datapizza.tools import tool

load_dotenv()

# Change this value to switch provider: "google" or "openai"
PROVIDER = "google"

SYSTEM_PROMPT = "You are a helpful assistant that can answer questions and help with tasks."

@tool
def add(a : float | int, b : float | int) -> str:
    """Performs addition safely."""
    return str(a + b)

if PROVIDER == "openai":
    client = OpenAIClient(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-5",
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


response = client.invoke(
    "Add 100 and 24.", 
    tools=[add])

print(response.function_calls)

result = add(**response.function_calls[0].arguments)

print("The result is: ", result)
