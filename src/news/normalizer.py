# src/news/normalizer.py
# Deduplicate, score-rank, and tag items by topic.
# Runs entirely in-memory. Zero user data.

import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher

from .sources import NewsItem


def normalize(items: list[NewsItem]) -> list[NewsItem]:
    """Deduplicate by URL + title similarity, then score-rank."""
    seen_urls: set[str] = set()
    unique: list[NewsItem] = []

    for item in sorted(items, key=lambda x: x.score or 0, reverse=True):
        if item.url and item.url in seen_urls:
            continue
        is_dup = False
        for prev in unique:
            if _similar(item.title, prev.title, threshold=0.75):
                is_dup = True
                break
        if not is_dup:
            if item.url:
                seen_urls.add(item.url)
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
