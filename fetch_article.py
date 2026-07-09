"""
Pulls today's Dawn content via official RSS feeds.

Fixes applied in this version:
- feedparser.parse(url) fetches with no User-Agent header by default, which
  some sites silently reject (returns empty/blocked response -> "no entries
  found"). We now fetch the feed bytes ourselves with a browser-like UA via
  requests, then hand the bytes to feedparser -- much more reliable.
- "/feeds/editorial" is not a confirmed-working Dawn feed URL. This version
  tries a small ordered list of candidate feeds and uses the first one that
  actually returns entries, instead of hardcoding one unconfirmed URL and
  crashing if it's wrong.
- Article body extraction grabs all <p> tags (Dawn doesn't reliably wrap
  content in one predictable class), trims known trailing boilerplate, and
  falls back to the og:description meta tag if paragraph scraping is thin.
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Tried in order; first one that returns entries wins. dawn.com/feeds/home
# is a confirmed-live feed; the others are attempted first since they're
# more specifically "editorial", but we don't depend on any single one.
EDITORIAL_FEED_CANDIDATES = [
    "https://www.dawn.com/feeds/opinion",
    "https://www.dawn.com/feeds/editorial",
    "https://www.dawn.com/feeds/home",
]

HEADLINE_FEED_CANDIDATES = [
    "https://www.dawn.com/feeds/home",
    "https://www.dawn.com/feeds/pakistan",
    "https://www.dawn.com/feeds/world",
]

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


def _parse_feed(url: str):
    """Fetch feed bytes ourselves (with a real User-Agent) then parse, since
    feedparser's own fetch sends no UA and can get silently blocked."""
    resp = _fetch_with_retry(url, retries=2, timeout=15)
    if resp is None:
        return None
    parsed = feedparser.parse(resp.content)
    if parsed.entries:
        return parsed
    return None


def _first_working_feed(candidates: list):
    for url in candidates:
        print(f"[fetch] trying feed: {url}")
        parsed = _parse_feed(url)
        if parsed:
            print(f"[fetch] success: {url} ({len(parsed.entries)} entries)")
            return parsed, url
    return None, None


def _fetch_full_text(url: str) -> str:
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

    meta = soup.find("meta", property="og:description")
    if meta and meta.get("content"):
        return meta["content"].strip()

    return ""


def get_latest_editorial() -> dict:
    """Returns {'title', 'link', 'summary', 'full_text', 'source'} for the newest editorial/opinion piece."""
    feed, used_url = _first_working_feed(EDITORIAL_FEED_CANDIDATES)
    if feed is None:
        raise RuntimeError(
            "All Dawn feed candidates failed (opinion, editorial, home). "
            "This is likely a temporary Dawn outage or a network block on the "
            "GitHub runner -- try again shortly. Candidates tried: "
            + ", ".join(EDITORIAL_FEED_CANDIDATES)
        )

    entry = feed.entries[0]
    title = entry.get("title", "Untitled")
    link = entry.get("link", "")
    summary = re.sub("<[^<]+?>", "", entry.get("summary", "")).strip()

    full_text = _fetch_full_text(link) if link else ""
    source = f"full_article ({used_url})"
    if not full_text or len(full_text) < 100:
        full_text = summary
        source = f"rss_summary_fallback ({used_url})"

    if not full_text:
        full_text = title
        source = f"title_only_fallback ({used_url})"

    return {"title": title, "link": link, "summary": summary, "full_text": full_text, "source": source}


def get_headline_pool(limit_per_feed: int = 15) -> list:
    """Pulls recent headlines for MCQ/bulletin variety. Skips any feed that
    fails instead of crashing the whole run."""
    headlines = []
    for feed_url in HEADLINE_FEED_CANDIDATES:
        parsed = _parse_feed(feed_url)
        if not parsed:
            print(f"[fetch] skipping headline feed (failed): {feed_url}")
            continue
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
