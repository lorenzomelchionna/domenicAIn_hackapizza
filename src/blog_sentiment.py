"""Blog scraping and sentiment classification for Hackapizza 2.0.

Reads the latest Cronache del Cosmo blog post and classifies the market mood
into a predefined sentiment from the sentiment pool. Used at the start of each
speaking phase to guide recipe filtering strategy.
"""
from typing import Optional

from datapizza.agents import Agent
from datapizza.tools import tool

from src.blog_archetype import _scrape_post
from src.config import REGOLO_API_KEY, REGOLO_BASE_URL, REGOLO_MODEL
from src.data import load_json

SENTIMENT_POOL: dict[str, str] = load_json("sentiments.json")


def extract_sentiment(response_text: str) -> Optional[str]:
    """Parse agent response for a sentiment key. Returns the key or None."""
    if not response_text:
        return None
    text_lower = response_text.lower()
    for key in SENTIMENT_POOL:
        if key in text_lower:
            return key
    return None


def run_sentiment_agent(post_index: int = 0) -> tuple[Optional[str], str]:
    """Run the blog sentiment agent. Returns (sentiment_or_none, full_response_text)."""
    from datapizza.clients.openai_like import OpenAILikeClient

    client = OpenAILikeClient(
        api_key=REGOLO_API_KEY,
        model=REGOLO_MODEL,
        base_url=REGOLO_BASE_URL,
    )

    @tool
    def get_blog_post(**kwargs: object) -> str:
        return _scrape_post(post_index)

    sentiment_descriptions = "\n".join(
        f"- **{key}**: {desc}" for key, desc in SENTIMENT_POOL.items() if key != "default"
    )

    agent = Agent(
        name="SentimentAgent",
        client=client,
        system_prompt=(
            "You read a blog post from Cronache del Cosmo and classify the market mood.\n\n"
            "Available sentiments:\n"
            f"{sentiment_descriptions}\n\n"
            "RULES:\n"
            "1. Call get_blog_post to read the latest post.\n"
            "2. Classify the post mood into EXACTLY ONE sentiment from the list above.\n"
            "3. Reply with ONLY the sentiment key (e.g. ricette_veloci). Nothing else.\n"
            "4. If unsure, reply with: default"
        ),
        tools=[get_blog_post],
    )

    resp = agent.run("Read the latest blog post and classify its market sentiment.")
    text = resp.text if hasattr(resp, "text") else str(resp)
    sentiment = extract_sentiment(text)
    return sentiment, text
