"""ClientFactory: create LLM clients for multiple providers with a single API.

Usage: python 01_clients/client_factory.py
Requires: OPENAI_API_KEY, GOOGLE_API_KEY in .env
"""
import os
from dotenv import load_dotenv

from datapizza.clients import ClientFactory
from datapizza.clients.factory import Provider

load_dotenv()

openai = ClientFactory.create(
    provider=Provider.OPENAI,
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-5",
    temperature=None
)

google = ClientFactory.create(
    provider=Provider.GOOGLE,
    api_key=os.getenv("GOOGLE_API_KEY"),
    model="gemini-flash-latest",
)

# anthropic = ClientFactory.create(
#     provider=Provider.ANTHROPIC,
#     api_key=os.getenv("ANTHROPIC_API_KEY"),
#     model="claude-3-5-sonnet-20240620",
# )

openai_response = openai.invoke("Explain agentic AI in one sentence.")
print("OpenAI response: ", openai_response.text)

google_response = google.invoke("Explain agentic AI in one sentence.")
print("Google response: ", google_response.text)
