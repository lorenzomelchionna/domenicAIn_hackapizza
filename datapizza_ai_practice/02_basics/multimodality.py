"""Multimodal input: send images (URL, base64, file path) alongside text prompts.

Usage: python 02_basics/multimodality.py
Requires: OPENAI_API_KEY or GOOGLE_API_KEY in .env
"""
import os
from dotenv import load_dotenv
import base64

from datapizza.clients.openai import OpenAIClient
from datapizza.clients.google import GoogleClient

from datapizza.type import Media, MediaBlock, TextBlock

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

# URL image
# media = Media(
#     extension="jpg",
#     media_type="image",
#     source_type="url",
#     source="https://mir-s3-cdn-cf.behance.net/project_modules/fs_webp/17af9a53451651.59356b7a6e040.jpg",
# )

# Base64 image
# with open("hackapizza_dataset/Misc/pizzaverse.png", "rb") as f:
#     image_data = base64.b64encode(f.read()).decode()

# media = Media(
#     extension="png",
#     media_type="image",
#     source_type="base64",
#     source=image_data,
# )

# Path image
media = Media(
    extension="png",
    media_type="image",
    source_type="path",
    source="hackapizza_dataset/Misc/pizzaverse.png",
)

response = client.invoke(
    [TextBlock(content="Describe the image in detail."), MediaBlock(media=media)],
)

print(response.text)
