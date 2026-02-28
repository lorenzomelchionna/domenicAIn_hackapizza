"""Conversation memory: interactive chatbot that remembers previous turns.

Usage: python 02_basics/memory.py  (type 'quit' to exit)
Requires: OPENAI_API_KEY or GOOGLE_API_KEY in .env
"""
import os
from dotenv import load_dotenv

from datapizza.clients.openai import OpenAIClient
from datapizza.clients.google import GoogleClient

from datapizza.memory import Memory
from datapizza.type import ROLE, TextBlock

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

memory = Memory()

print("Chatbot: Hello! I'm here to help. Type 'quit' to exit.")

while True:
    user_input = input("\nYou: ")
    if user_input.lower() == "quit":
        break

    response = client.invoke(user_input, memory=memory)
    print(f"Chatbot: {response.text}")

    memory.add_turn(TextBlock(content=user_input), role=ROLE.USER)
    memory.add_turn(response.content, role=ROLE.ASSISTANT)
