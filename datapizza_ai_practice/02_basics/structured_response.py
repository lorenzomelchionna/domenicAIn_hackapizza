"""Structured output: extract typed data from text using Pydantic models.

Usage: python 02_basics/structured_response.py
Requires: OPENAI_API_KEY or GOOGLE_API_KEY in .env
"""
import os
from dotenv import load_dotenv
from pydantic import BaseModel

from datapizza.clients.openai import OpenAIClient
from datapizza.clients.google import GoogleClient

load_dotenv()

# Change this value to switch provider: "google" or "openai"
PROVIDER = "openai"

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

class Actor(BaseModel):
    name: str
    role: str

class MovieDescription(BaseModel):
    movie_title: str
    genre: str
    year: int
    director: str
    actors: list[Actor]

movie_text = "Taxi Driver is a 1976 psychological thriller directed by Martin Scorsese, starring Robert De Niro as Travis Bickle, a troubled, insomniac Vietnam War veteran who works night shifts as a taxi driver in gritty 1970s New York City. Disgusted by urban decay, crime, and moral corruption, Travis spirals into isolation and violent fantasies, obsessing over a political campaign worker (Cybill Shepherd) and attempting to \"rescue\" a teenage prostitute (Jodie Foster) from her pimp (Harvey Keitel). His descent culminates in a bloody vigilante rampage that blurs the line between heroism and madness, earning acclaim as a landmark of American cinema for its raw exploration of alienation and rage."

prompt = f"Given an input movie text, convert it to a struvctured object: {movie_text}."

response = client.structured_response(input=prompt, output_cls=MovieDescription)

movie_description = response.structured_data[0]

print(movie_description)
print(movie_description.movie_title)
print(movie_description.genre)
print(movie_description.year)
print(movie_description.director)
print(movie_description.actors)
