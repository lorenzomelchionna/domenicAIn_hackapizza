"""Local LLM via Ollama using the OpenAILikeClient wrapper.

Usage: python 01_clients/ollama.py
Requires: Ollama running locally on port 11434
"""
from datapizza.clients.openai_like import OpenAILikeClient

client = OpenAILikeClient(
    api_key = "", # Ollama does not use an API key
    model = "gemma3:4b",
    system_prompt = "You are a helpful assistant that can answer questions and help with tasks.",
    base_url = "http://localhost:11434/v1"
)

response = client.invoke("Explain agentic AI in one sentence.")
print("Response: ", response.text)
