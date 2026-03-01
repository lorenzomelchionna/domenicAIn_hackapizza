"""Blog scraping and market insight extraction for Hackapizza 2.0.

Reads the latest Cronache del Cosmo blog post and produces a free-form
strategic insight about what kind of recipes to favour this turn.
Used at the start of each speaking phase to guide recipe selection.
"""
from datapizza.agents import Agent
from datapizza.tools import tool

from src.blog_archetype import _scrape_post
from src.config import REGOLO_API_KEY, REGOLO_BASE_URL, REGOLO_MODEL


def run_blog_insight_agent(post_index: int = 0) -> str:
    """Read the latest blog post and return a strategic insight for menu planning.

    Returns the agent's free-form analysis as a string.
    """
    from datapizza.clients.openai_like import OpenAILikeClient

    client = OpenAILikeClient(
        api_key=REGOLO_API_KEY,
        model=REGOLO_MODEL,
        base_url=REGOLO_BASE_URL,
    )

    @tool
    def get_blog_post(**kwargs: object) -> str:
        return _scrape_post(post_index)

    agent = Agent(
        name="BlogInsightAgent",
        client=client,
        system_prompt=(
            "You are a market analyst for a galactic restaurant.\n"
            "Read the latest blog post from Cronache del Cosmo and extract a concise "
            "strategic insight that will guide menu planning.\n\n"
            "Your output MUST be a short paragraph (3-5 sentences) that answers:\n"
            "- What kind of customers are expected? (e.g. budget-conscious, premium, families, in a hurry)\n"
            "- What qualities should the menu emphasise? (e.g. fast prep, high prestige, low cost, variety, niche dishes)\n"
            "- Any other actionable hint from the post.\n\n"
            "Be specific and actionable. Do NOT list sentiment labels. "
            "Write in English. Do NOT include the blog text itself."
        ),
        tools=[get_blog_post],
    )

    resp = agent.run("Read the latest blog post and produce a strategic menu insight.")
    return resp.text if hasattr(resp, "text") else str(resp)
