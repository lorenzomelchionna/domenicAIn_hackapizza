"""Streaming responses: print LLM output token-by-token as it arrives.

Usage: python 01_clients/streaming_response.py
Requires: OPENAI_API_KEY or GOOGLE_API_KEY in .env
"""
import os
from dotenv import load_dotenv

from datapizza.clients.openai import OpenAIClient
from datapizza.clients.google import GoogleClient

load_dotenv()

# Change this value to switch provider: "google" or "openai"
PROVIDER = "google"

SYSTEM_PROMPT = "You are a helpful assistant that can answer questions and help with tasks."

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

response = client.stream_invoke("Explain agentic AI in one paragraph.")

for chunk in response:
    print(chunk.delta, end="", flush=True)
