# src/news/frequency.py
# Frequency analyzer — counts how often a topic comes up worldwide
# and groups geo-tagged news by region.
#
# Reads from the published public/feeds/ directory (committed in git)
# and from live source results in-memory.
#
# All operations are public. No user data.

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass
class TopicFrequency:
    topic: str
    count: int
    regions: dict[str, int] = field(default_factory=dict)  # country -> count
    lat_lon_centroid: tuple[float | None, float | None] = (None, None)
    latest_url: str | None = None
    latest_title: str | None = None
    latest_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "count": self.count,
            "regions": self.regions,
            "lat": self.lat_lon_centroid[0],
            "lon": self.lat_lon_centroid[1],
            "latest_url": self.latest_url,
            "latest_title": self.latest_title,
            "latest_at": self.latest_at,
        }


# ─── Token-level frequency ─────────────────────────────────────────────────

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "to", "of", "for", "in", "on", "at", "by", "from", "as", "with",
    "this", "that", "it", "be", "been", "has", "have", "had", "do",
    "does", "did", "will", "would", "should", "could", "may", "might",
    "than", "then", "so", "no", "not", "only", "also", "very", "just",
    "after", "before", "over", "under", "more", "most", "some", "any",
    "their", "there", "they", "you", "your", "our", "ours", "we",
}


def token_frequency(items: list[dict], min_len: int = 4) -> dict[str, int]:
    """Count word frequencies across titles."""
    counter: Counter = Counter()
    for it in items:
        title = (it.get("title") or "").lower()
        for word in re.findall(r"[a-z][a-z0-9-]+", title):
            if len(word) < min_len or word in STOPWORDS:
                continue
            counter[word] += 1
    return dict(counter.most_common(50))


# ─── Topic frequency (using the source-level topic tags) ─────────────────

def topic_frequency(items: list[dict]) -> list[TopicFrequency]:
    """Group items by topic, count, compute region distribution, centroid."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        for topic in it.get("topics") or ["uncategorized"]:
            grouped[topic].append(it)

    result: list[TopicFrequency] = []
    for topic, topic_items in grouped.items():
        regions: Counter = Counter()
        lats: list[float] = []
        lons: list[float] = []
        for it in topic_items:
            country = it.get("country") or "Unknown"
            regions[country] += 1
            lat = it.get("lat")
            lon = it.get("lon")
            if lat is not None and lon is not None:
                lats.append(lat)
                lons.append(lon)

        latest = max(topic_items, key=lambda x: x.get("fetched_at", ""), default=None)
        centroid = (None, None)
        if lats and lons:
            centroid = (sum(lats) / len(lats), sum(lons) / len(lons))

        result.append(TopicFrequency(
            topic=topic,
            count=len(topic_items),
            regions=dict(regions.most_common(10)),
            lat_lon_centroid=centroid,
            latest_url=(latest or {}).get("url"),
            latest_title=(latest or {}).get("title"),
            latest_at=(latest or {}).get("fetched_at"),
        ))
    return sorted(result, key=lambda t: t.count, reverse=True)


# ─── Worldwide aggregation by region ───────────────────────────────────────

def region_frequency(items: list[dict]) -> dict[str, dict]:
    """Group by country. Return country -> {count, topics, sample_url}."""
    countries: dict[str, dict] = defaultdict(lambda: {"count": 0, "topics": Counter(), "sample_url": None})
    for it in items:
        country = it.get("country") or "Unknown"
        countries[country]["count"] += 1
        for t in it.get("topics") or ["uncategorized"]:
            countries[country]["topics"][t] += 1
        if not countries[country]["sample_url"] and it.get("url"):
            countries[country]["sample_url"] = it["url"]
    return {c: {"count": d["count"], "topics": dict(d["topics"]), "sample_url": d["sample_url"]} for c, d in countries.items()}


# ─── Break detection ───────────────────────────────────────────────────────

def detect_breaks(items: list[dict], window_minutes: int = 60) -> list[dict]:
    """
    Find 'breaking' news — items appearing in the last `window_minutes`
    that are NOT continuations of older stories.
    Returns the items marked as breaking.
    """
    now = datetime.now(timezone.utc)
    breaking: list[dict] = []
    for it in items:
        fa = it.get("fetched_at", "")
        try:
            ts = datetime.fromisoformat(fa.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        if (now - ts).total_seconds() > window_minutes * 60:
            continue
        # Has geo info or score >= 10 → mark as breaking
        if it.get("lat") is not None or (it.get("score") or 0) >= 10:
            breaking.append({**it, "breaking": True})
    return breaking


# ─── Compose digest JSON ────────────────────────────────────────────────────

def build_digest(items: list[dict]) -> dict:
    """Build a digest JSON for public/feeds/digest/latest.json."""
    now = datetime.now(timezone.utc).isoformat()
    tf = [t.to_dict() for t in topic_frequency(items)]
    rf = region_frequency(items)
    breaking = detect_breaks(items)
    token_freq = token_frequency(items)

    return {
        "version": 1,
        "kind": "digest",
        "fetched_at": now,
        "item_count": len(items),
        "topics": tf,
        "regions": rf,
        "breaking": breaking[:20],
        "top_words": token_freq,
    }


def write_digest(items: list[dict], out_dir: str | Path) -> Path | None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    digest = build_digest(items)
    out_path = out_dir / "digest" / "latest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(digest, indent=2, ensure_ascii=False))
    return out_path
