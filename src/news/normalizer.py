# src/news/normalizer.py
# Deduplicate, score-rank, and tag items by topic.
# Runs entirely in-memory. Zero user data.

import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

from .sources import NewsItem


# Tracking params that don't affect article identity. Strip these before
# URL dedup so the same article from two different sources collapses.
_TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src",
    "ref_url", "source", "ncid", "feature", "sr_share",
})


def _canonical_url(url: str) -> str:
    """Strip tracking params + fragment for dedup. Returns the raw url on
    any parse error (defensive)."""
    try:
        u = urlparse(url)
        if not u.netloc:
            return url
        # Drop tracking query params, keep only order-stable
        qs = parse_qs(u.query, keep_blank_values=False)
        qs = {k: v for k, v in qs.items() if k not in _TRACKING_PARAMS}
        new_query = urlencode(qs, doseq=True) if qs else ""
        return urlunparse((u.scheme, u.netloc, u.path, u.params, new_query, ""))
    except (ValueError, AttributeError):
        return url


def normalize(items: list[NewsItem]) -> list[NewsItem]:
    """Deduplicate by URL + title similarity, then score-rank."""
    seen_urls: set[str] = set()
    unique: list[NewsItem] = []

    for item in sorted(items, key=lambda x: x.score or 0, reverse=True):
        canon = _canonical_url(item.url) if item.url else ""
        if canon and canon in seen_urls:
            continue
        is_dup = False
        for prev in unique:
            if _similar(item.title, prev.title, threshold=0.75):
                is_dup = True
                break
        if not is_dup:
            if canon:
                seen_urls.add(canon)
            unique.append(item)

    for item in unique:
        item.score = _rerank(item)
    return sorted(unique, key=lambda x: x.score or 0, reverse=True)


def _similar(a: str, b: str, threshold: float) -> bool:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold


def _rerank(item: NewsItem) -> int:
    score = item.score or 0
    topic_bonus = {
        "ai": 50, "llm": 50, "security": 40, "vulnerability": 40,
        "zero-day": 40, "privacy": 30, "cloud": 20, "infrastructure": 20,
        "open-source": 15,
    }
    for topic in item.topics:
        score += topic_bonus.get(topic, 5)
    return min(score, 1000)


def group_by_topic(items: list[NewsItem]) -> dict[str, list[NewsItem]]:
    buckets: dict[str, list[NewsItem]] = defaultdict(list)
    for item in items:
        if item.topics:
            for t in item.topics:
                buckets[t].append(item)
        else:
            buckets["uncategorized"].append(item)
    return dict(buckets)
