"""Blog scraping and archetype identification for Hackapizza 2.0.

Runs the Cronache del Cosmo blog agent to identify target customer archetype
from market signals. Used at the start of each speaking phase.
"""
import re
from typing import Optional

import requests
from datapizza.agents import Agent
from datapizza.tools import tool

from src.config import REGOLO_API_KEY, REGOLO_BASE_URL, REGOLO_MODEL

BLOG_URL = "https://hackablog.datapizza.tech"

# Canonical names for menu_decider_pre_bid (underscore format)
ARCHETYPE_MAP = {
    "esploratore galattico": "Esploratore_Galattico",
    "astrobarone": "Astrobarone",
    "saggi del cosmo": "Saggi_del_Cosmo",
    "famiglie orbitali": "Famiglie_Orbitali",
}

DEFAULT_ARCHETYPE = "Astrobarone"


def _scrape_post(index: int = 0) -> str:
    """Fetch blog post content. index=0 is most recent."""
    try:
        resp = requests.get(f"{BLOG_URL}/", timeout=15)
        resp.raise_for_status()
        html = resp.text

        seen = set()
        post_slugs = []
        for m in re.finditer(r'href="/([a-z0-9-]+/)"', html):
            slug = m.group(1)
            if slug not in ("tag/", "page/", "rss/", "webmentions/") and slug not in seen:
                seen.add(slug)
                post_slugs.append(slug)

        if not post_slugs or index >= len(post_slugs):
            return "Error: Could not find post."

        post_url = f"{BLOG_URL}/{post_slugs[index]}"
        post_resp = requests.get(post_url, timeout=15)
        post_resp.raise_for_status()
        post_html = post_resp.text

        title_match = re.search(r"<title>([^<]+)</title>", post_html)
        title = title_match.group(1).strip() if title_match else "Unknown"

        article_match = re.search(
            r'<article[^>]*class="[^"]*gh-article[^"]*"[^>]*>(.*?)</article>',
            post_html,
            re.DOTALL,
        )
        if article_match:
            content = re.sub(r"<[^>]+>", " ", article_match.group(1))
            content = re.sub(r"\s+", " ", content).strip()
        else:
            paras = re.findall(r"<p[^>]*>(.*?)</p>", post_html)
            content = " ".join(re.sub(r"<[^>]+>", "", p) for p in paras if len(p) > 20)

        return f"Title: {title}\nURL: {post_url}\n\nContent:\n{content}"
    except Exception as e:
        return f"Error fetching blog: {e}"


def extract_archetype(response_text: str) -> Optional[str]:
    """Parse agent response for identified archetype. Returns canonical name or None."""
    if not response_text:
        return None
    text_lower = response_text.lower()
    for key, canonical in ARCHETYPE_MAP.items():
        if key in text_lower:
            return canonical
    return None


def run_archetype_agent(post_index: int = 0) -> tuple[Optional[str], str]:
    """Run the blog archetype agent. Returns (archetype_or_none, full_response_text)."""
    from datapizza.clients.openai_like import OpenAILikeClient

    client = OpenAILikeClient(
        api_key=REGOLO_API_KEY,
        model=REGOLO_MODEL,
        base_url=REGOLO_BASE_URL,
    )

    @tool
    def get_blog_post(**kwargs: object) -> str:
        return _scrape_post(post_index)

    ARCHETYPE_DEFS = """
- **Esploratore Galattico**: poco tempo, poco budget. Premia: piatti semplici, economici, rapidissimi.
- **Astrobarone**: pochissimo tempo, buoni piatti, guarda poco al prezzo. Premia: qualità, rapidità, status.
- **Saggi del Cosmo**: ottimi piatti, tempo da perdere, badano poco al prezzo. Premia: ricette prestigiose, ingredienti rari.
- **Famiglie Orbitali**: molto tempo, osservano prezzo e qualità. Premia: equilibrio costo/valore, piatti curati ma accessibili.
"""

    agent = Agent(
        name="ArchetypeAgent",
        client=client,
        system_prompt=f"""Read a blog post from Cronache del Cosmo and extract insights.
{ARCHETYPE_DEFS}
If you identify a target archetype with confidence (explicit or strongly implied), say it explicitly with name.
Otherwise extract the key message briefly. Do NOT invent an archetype.""",
        tools=[get_blog_post],
    )

    resp = agent.run(
        "Read the blog post. If you identify a target archetype with confidence, say it explicitly. "
        "Otherwise extract the key message briefly."
    )
    text = resp.text if hasattr(resp, "text") else str(resp)
    archetype = extract_archetype(text)
    return archetype, text
