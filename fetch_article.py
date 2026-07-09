"""
Pulls today's Dawn content via official RSS feeds (stable, unlike scraping
the homepage HTML which breaks whenever Dawn changes their site design).

Fixes applied here vs the earlier version:
- Retries the HTTP request instead of giving up on the first failure.
- Extracts ALL <p> tags on the page (Dawn doesn't reliably wrap article body
  in one predictable class name), then trims trailing boilerplate
  ("Published in Dawn...", "Our readers are at the heart...", nav/footer
  junk) instead of relying on a single CSS selector that can silently match
  nothing.
- Falls back to the RSS <summary> AND the page's og:description meta tag
  before giving up, so "article unavailable" should no longer happen except
  in a genuine network outage.
"""
import re
import time
import feedparser
import requests
from bs4 import BeautifulSoup
import config

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Paragraphs at/after any of these (case-insensitive, prefix match) are Dawn's
# standard trailing boilerplate, not article content -- cut everything from
# the first match onward.
STOP_MARKERS = [
    "published in dawn",
    "our readers are at the heart",
    "read more",
    "follow dawn",
    "subscribe to newspaper",
]


def _fetch_with_retry(url: str, retries: int = 3, timeout: int = 20):
    last_exc = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_exc = e
            time.sleep(1 + attempt)
    print(f"[fetch] giving up on {url}: {last_exc}")
    return None


def _fetch_full_text(url: str) -> str:
    """Best-effort full article text extraction from a Dawn article page."""
    resp = _fetch_with_retry(url)
    if resp is None:
        return ""

    soup = BeautifulSoup(resp.content, "lxml")
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    paragraphs = [p for p in paragraphs if len(p) > 25]

    cleaned = []
    for p in paragraphs:
        low = p.lower()
        if any(low.startswith(marker) for marker in STOP_MARKERS):
            break
        cleaned.append(p)

    text = "\n".join(cleaned).strip()
    if len(text) > 100:
        return text

    # Fallback: og:description meta tag (usually a 1-2 sentence dek, better
    # than nothing if paragraph scraping failed).
    meta = soup.find("meta", property="og:description")
    if meta and meta.get("content"):
        return meta["content"].strip()

    return ""


def get_latest_editorial() -> dict:
    """Returns {'title', 'link', 'summary', 'full_text', 'source'} for the newest editorial."""
    feed = feedparser.parse(config.DAWN_EDITORIAL_FEED)
    if not feed.entries:
        raise RuntimeError("No entries found in Dawn editorial feed -- feed may be down.")

    entry = feed.entries[0]
    title = entry.get("title", "Untitled")
    link = entry.get("link", "")
    summary = re.sub("<[^<]+?>", "", entry.get("summary", "")).strip()

    full_text = _fetch_full_text(link) if link else ""
    source = "full_article"
    if not full_text or len(full_text) < 100:
        full_text = summary
        source = "rss_summary_fallback"

    if not full_text:
        # Absolute last resort so the pipeline never sends "unavailable"
        # silently -- at minimum we always have the headline.
        full_text = title
        source = "title_only_fallback"

    return {
        "title": title,
        "link": link,
        "summary": summary,
        "full_text": full_text,
        "source": source,
    }


def get_headline_pool(limit_per_feed: int = 15) -> list:
    """Pulls recent Pakistan + World + Home headlines for MCQ/bulletin variety."""
    feeds = [config.DAWN_PAKISTAN_FEED, config.DAWN_WORLD_FEED, config.DAWN_HOME_FEED]
    headlines = []
    for feed_url in feeds:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries[:limit_per_feed]:
            summary = re.sub("<[^<]+?>", "", entry.get("summary", "")).strip()
            headlines.append(
                {"title": entry.get("title", ""), "summary": summary, "link": entry.get("link", "")}
            )
    return headlines


if __name__ == "__main__":
    art = get_latest_editorial()
    print(f"[{art['source']}] {art['title']}")
    print(art["full_text"][:500])
