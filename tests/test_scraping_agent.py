#!/usr/bin/env python3
"""Scraping agent that reads the last blog post from https://hackablog.datapizza.tech/
and identifies which customer archetype to target based on the market signals.

Usage:
  python tests/test_scraping_agent.py              # With LLM: fetch latest + extract insights
  python tests/test_scraping_agent.py --index 1     # Second most recent post (0=latest, 1=prev, ...)
  python tests/test_scraping_agent.py --no-llm     # Without LLM: fetch and print raw content

Requires: REGOLO_API_KEY or OPENAI_API_KEY in .env (for LLM mode)
"""
import os
import re
import sys
from pathlib import Path

# Add project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import requests
from datapizza.tools import tool
from datapizza.agents import Agent

# Client setup: prefer Regolo (project default), fallback to OpenAI
REGOLO_API_KEY = os.getenv("REGOLO_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if REGOLO_API_KEY:
    from datapizza.clients.openai_like import OpenAILikeClient
    client = OpenAILikeClient(
        api_key=REGOLO_API_KEY,
        model=os.getenv("REGOLO_MODEL", "gpt-oss-120b"),
        base_url=os.getenv("REGOLO_BASE_URL", "https://api.regolo.ai/v1"),
    )
elif OPENAI_API_KEY:
    from datapizza.clients.openai import OpenAIClient
    client = OpenAIClient(
        api_key=OPENAI_API_KEY,
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )
else:
    raise ValueError("Set REGOLO_API_KEY or OPENAI_API_KEY in .env")

BASE_URL = "https://hackablog.datapizza.tech"


# Post index for tool (set by main from --index arg)
_post_index = 0


def _scrape_post(index: int = 0) -> str:
    """Fetch and return the full content of a blog post from Cronache del Cosmo (hackablog.datapizza.tech).
    index=0 is the most recent, index=1 the second, etc.
    Returns title, author, date, and full article text."""
    try:
        # 1. Fetch homepage
        resp = requests.get(f"{BASE_URL}/", timeout=15)
        resp.raise_for_status()
        html = resp.text

        # 2. Collect all post slugs in order (exclude tag/, page/, rss, etc.)
        seen = set()
        post_slugs = []
        for m in re.finditer(r'href="/([a-z0-9-]+/)"', html):
            slug = m.group(1)
            if slug not in ("tag/", "page/", "rss/", "webmentions/") and slug not in seen:
                seen.add(slug)
                post_slugs.append(slug)

        if not post_slugs:
            return "Error: Could not find any post links on the homepage."

        if index >= len(post_slugs):
            return f"Error: Post index {index} out of range. Found {len(post_slugs)} posts (use 0 to {len(post_slugs) - 1})."

        post_url = f"{BASE_URL}/{post_slugs[index]}"

        # 3. Fetch the post page
        post_resp = requests.get(post_url, timeout=15)
        post_resp.raise_for_status()
        post_html = post_resp.text

        # 4. Extract title
        title_match = re.search(r"<title>([^<]+)</title>", post_html)
        title = title_match.group(1).strip() if title_match else "Unknown"

        # 5. Extract article body (Ghost uses gh-article)
        article_match = re.search(
            r'<article[^>]*class="[^"]*gh-article[^"]*"[^>]*>(.*?)</article>',
            post_html,
            re.DOTALL,
        )
        if article_match:
            content_html = article_match.group(1)
            # Strip HTML, normalize whitespace
            content = re.sub(r"<[^>]+>", " ", content_html)
            content = re.sub(r"\s+", " ", content).strip()
        else:
            # Fallback: get all paragraphs
            paras = re.findall(r"<p[^>]*>(.*?)</p>", post_html)
            content = " ".join(re.sub(r"<[^>]+>", "", p) for p in paras if len(p) > 20)

        return f"Title: {title}\nURL: {post_url}\n\nContent:\n{content}"
    except requests.RequestException as e:
        return f"Error fetching blog: {e}"
    except Exception as e:
        return f"Error: {e}"


def _get_hackablog_post_impl(**kwargs: object) -> str:
    """Fetch post at _post_index (0=latest, 1=second, etc.)."""
    return _scrape_post(_post_index)


@tool
def get_last_hackablog_post(**kwargs: object) -> str:
    """Fetch and return the full content of a blog post from Cronache del Cosmo (hackablog.datapizza.tech).
    By default returns the most recent post. Call with no arguments."""
    return _get_hackablog_post_impl(**kwargs)


ARCHETYPE_DEFINITIONS = """
## Archetipi del Multiverso (Hackapizza 2.0)

- **🚀 Esploratore Galattico**: Viaggiatore instancabile. Ha poco tempo, poco budget, qualità non priorità.
  Cosa premia: piatti semplici, economici e rapidissimi.

- **💰 Astrobarone**: Magnate interstellare. Ha pochissimo tempo, pretende buoni piatti, guarda poco al prezzo.
  Cosa premia: qualità, rapidità e un menu che comunichi status e prestigio.

- **🔭 Saggi del Cosmo**: Entità contemplative, studiosi del gusto. Cercano ottimi piatti, hanno tempo da perdere, badano poco al prezzo.
  Cosa premia: ricette prestigiose, ingredienti rari, coerenza narrativa e culturale.

- **👨‍👩‍👧‍👦 Famiglie Orbitali**: Nuclei familiari delle colonie spaziali. Hanno molto tempo, osservano prezzo e qualità.
  Cosa premia: equilibrio tra costo e valore, piatti curati ma accessibili, menu ben progettato.
"""

SYSTEM_PROMPT = f"""You are a strategy assistant for Hackapizza 2.0. Your job is to read a blog post from Cronache del Cosmo (hackablog.datapizza.tech) and extract actionable insights.

{ARCHETYPE_DEFINITIONS}

Workflow:
1. Call get_last_hackablog_post() to fetch the post (which post is controlled by the user).
2. Analyze the content and decide:
   - **If you can identify a target archetype with reasonable confidence** (explicitly named OR strongly implied by the post's signals): say it explicitly. Output the archetype (emoji + name), a brief justification, and menu implications.
   - **If the post does NOT allow a confident archetype match**: do NOT force one. Instead, extract the key message of the post and describe it briefly. Focus on market signals, trends, or advice that are useful even without a specific archetype."""

agent = Agent(
    name="Scraping Agent",
    client=client,
    system_prompt=SYSTEM_PROMPT,
    tools=[get_last_hackablog_post],
)


def main() -> None:
    import argparse
    global _post_index
    parser = argparse.ArgumentParser(description="Scrape Hackablog post")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM, just fetch and print raw content")
    parser.add_argument("--index", type=int, default=0, metavar="N", help="Post index: 0=latest, 1=second, 2=third, ... (default: 0)")
    args = parser.parse_args()

    _post_index = args.index

    if args.no_llm:
        label = "latest" if args.index == 0 else f"post #{args.index}"
        print(f"Fetching {label} blog post from https://hackablog.datapizza.tech/ ...\n")
        print(_scrape_post(args.index))
        return

    label = "latest" if args.index == 0 else f"post #{args.index}"
    print(f"Fetching {label} blog post and extracting insights...\n")
    response = agent.run(
        "Read the blog post. If you can identify a target archetype with reasonable confidence (explicit or strongly implied), say so explicitly with justification. "
        "Otherwise, do NOT invent one: extract the key message of the post and describe it briefly."
    )
    print(response.text if hasattr(response, "text") else response)


if __name__ == "__main__":
    main()
