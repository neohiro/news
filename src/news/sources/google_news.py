# src/news/sources/google_news.py
# Google News via free RSS + GDELT Project for geo-enriched articles.
# No API key required. Zero user data.
#
# Sources used:
#   - Google News RSS feeds (topic + search, no auth)
#   - GDELT Project (https://www.gdeltproject.org/) — real-time geo-tagged news DB
#     GDELT provides lat/lon for news events globally, free, no key.
#
# For gdelt: query the doc API at 15-min intervals; for GN RSS: hourly.
# All output is public. No user data.

from __future__ import annotations

import json
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.request import Request, urlopen


UA = "neohiro-news/1.0 (+https://github.com/neohiro/news)"


# ─── Google News RSS feeds (topic-based, no auth) ───────────────────────────
GN_RSS_TOPICS = {
    "world":          "https://news.google.com/rss?topic=w&hl=en&gl=US",
    "technology":     "https://news.google.com/rss?topic=t&hl=en&gl=US",
    "business":       "https://news.google.com/rss?topic=b&hl=en&gl=US",
    "science":        "https://news.google.com/rss?topic=s&hl=en&gl=US",
    "health":         "https://news.google.com/rss?topic=m&hl=en&gl=US",
    "sports":         "https://news.google.com/rss?topic=e&hl=en&gl=US",
    "entertainment":  "https://news.google.com/rss?topic=e&hl=en&gl=US",
    "ai":             "https://news.google.com/rss/search?q=artificial+intelligence&hl=en&gl=US",
    "cybersecurity":  "https://news.google.com/rss/search?q=cybersecurity&hl=en&gl=US",
    "climate":        "https://news.google.com/rss/search?q=climate+change&hl=en&gl=US",
}


@dataclass
class GeoItem:
    title: str
    url: str
    source: str
    lat: float | None
    lon: float | None
    country: str | None
    country_code: str | None
    fetched_at: str = ""
    topics: list[str] = field(default_factory=list)
    score: int = 0

    def __post_init__(self):
        if not self.fetched_at:
            self.fetched_at = datetime.now(timezone.utc).isoformat()


# ─── Google News RSS fetcher ─────────────────────────────────────────────────

def fetch_gn_rss(topic: str, limit: int = 10) -> list[GeoItem]:
    """Fetch Google News RSS for a topic. No API key."""
    url = GN_RSS_TOPICS.get(topic)
    if not url:
        return []
    items: list[GeoItem] = []
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except URLError:
        return items

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return items

    ns = _gn_ns(root)
    channel = root.find(f"{ns}channel")
    if channel is None:
        return items

    for item in channel.findall(f"{ns}item")[:limit]:
        title = _text(item, f"{ns}title")
        link  = _text(item, f"{ns}link")
        pub   = _text(item, f"{ns}pubDate")
        if not title:
            continue
        items.append(GeoItem(
            title=title,
            url=link or "",
            source=f"Google News/{topic}",
            lat=None,
            lon=None,
            country=None,
            country_code=None,
            topics=[topic],
        ))
    return items


def _gn_ns(root: ET.Element) -> str:
    tag = root.tag
    if tag.startswith("{"):
        return tag[1:].split("}")[0] + "}"
    return ""


def _text(el: ET.Element, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "").strip() if child is not None else ""


# ─── GDELT fetcher ─────────────────────────────────────────────────────────
# GDELT provides real-time geo-tagged news. Free, no key.
# Query: https://api.gdeltproject.org/api/v2/doc/doc?query=KEYWORD&mode=artlist&format=json&maxrecords=50
# We use the 15-min rolling GeoJSON feed for breaking news instead:
#   https://newsdata.io — free tier, no key for basic geo
#   https://www.gdeltproject.org/data/lookups/IONESTERMS.txt  (categories)
#
# For GDELT: use the GeoJSON endpoint (no key required)
GDELT_GEO_URL = "https://www.gdeltproject.org/data/lookups/CITYCOORDS.TXT"
GDELT_ARTICLES_URL = "https://api.gdeltproject.org/api/v2/doc/doc?query={q}&mode=artlist&format=json&maxrecords=25&sort=DateDesc"


def fetch_gdelt(query: str = "breaking", limit: int = 20) -> list[GeoItem]:
    """Fetch geo-tagged articles from GDELT. No API key."""
    q_encoded = urllib.parse.quote(query[:200])
    url = GDELT_ARTICLES_URL.format(q=q_encoded)
    items: list[GeoItem] = []
    try:
        req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        with urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except URLError:
        return items

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return items

    articles = data.get("articles", [])[:limit]
    for art in articles:
        title = (art.get("title") or "").strip()
        url_val = (art.get("url") or "").strip()
        if not title:
            continue
        # GDELT sometimes provides social image country
        country = art.get("domain") or ""
        # lat/lon come from GDELT's separate geo lookup; here we tag by domain country
        lat = None
        lon = None
        country_code = None
        items.append(GeoItem(
            title=title,
            url=url_val,
            source=art.get("domain", "GDELT"),
            lat=lat,
            lon=lon,
            country=country,
            country_code=country_code,
            topics=_detect_topics(title),
            score=art.get("socialimagecount", 0) or 0,
        ))
    return items


# ─── GDELT 15-min GeoJSON feed (breaking news with lat/lon) ────────────────
# This feed gives us lat/lon for breaking news events globally.
# Format: newline-delimited JSON, ~2MB per 15 min
# Endpoint: https://data.gdeltproject.org/internal/geojson/LAST15MIN.geojson
GDELT_GEOJSON_URL = "https://data.gdeltproject.org/internal/geojson/LAST15MIN.geojson"


def fetch_gdelt_geojson(limit: int = 50) -> list[GeoItem]:
    """Fetch breaking news with GPS coordinates from GDELT GeoJSON. No API key."""
    items: list[GeoItem] = []
    try:
        req = Request(GDELT_GEOJSON_URL, headers={"User-Agent": UA})
        with urlopen(req, timeout=20) as resp:
            raw = resp.read(512_000).decode("utf-8", errors="replace")
    except URLError:
        return items

    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            feat = json.loads(line)
        except json.JSONDecodeError:
            continue
        if feat.get("type") != "Feature":
            continue
        props = feat.get("properties", {}) or {}
        coords = feat.get("geometry", {}).get("coordinates", [])
        lon = coords[0] if len(coords) > 0 else None
        lat = coords[1] if len(coords) > 1 else None
        title = (props.get("title") or props.get("name") or "").strip()
        if not title:
            continue
        items.append(GeoItem(
            title=title,
            url=(props.get("url") or "").strip(),
            source="GDELT GeoJSON",
            lat=lat,
            lon=lon,
            country=props.get("country1", "") or None,
            country_code=props.get("country1code", "") or None,
            topics=_detect_topics(title),
            score=props.get("score", 0) or 0,
        ))
        if len(items) >= limit:
            break
    return items


# ─── Topic detector ──────────────────────────────────────────────────────────
TOPIC_KEYWORDS = {
    "ai":            ["ai", "artificial intelligence", "llm", "gpt", "claude", "gemini", "deepmind", "openai"],
    "security":      ["security", "breach", "hack", "vulnerability", "ransomware", "cve-", "exploit", "cyber"],
    "privacy":       ["privacy", "gdpr", "surveillance", "data protection"],
    "infrastructure":["cloud", "aws", "azure", "gcp", "kubernetes", "data center"],
    "climate":       ["climate", "carbon", "renewable", "emissions", "environment"],
    "geopolitics":   ["war", "sanctions", "nato", "eu ", "un ", "conflict", "military"],
    "science":       ["research", "study", "discovery", "scientist", "breakthrough"],
    "health":        ["health", "pandemic", "vaccine", "disease", "fda", "who "],
    "space":         ["space", "nasa", "spacex", "rocket", "satellite", "mars"],
    "finance":        ["economy", "inflation", "recession", "stock", "market", "fed "],
}


def _detect_topics(title: str) -> list[str]:
    t = title.lower()
    found = []
    for topic, kws in TOPIC_KEYWORDS.items():
        if any(k in t for k in kws):
            found.append(topic)
    return found or ["general"]


# ─── Register as news source ─────────────────────────────────────────────────

from urllib.error import URLError
from . import BaseSource, register_source


@register_source
class GoogleNewsSource(BaseSource):
    name = "google_news"

    def __init__(self, http_timeout: int = 15):
        self.http_timeout = http_timeout

    def fetch(self) -> list[dict]:
        """Return list of dicts (compatible with normalizer)."""
        all_items: list[dict] = []

        # Google News RSS per topic
        for topic in GN_RSS_TOPICS:
            for item in fetch_gn_rss(topic, limit=5):
                all_items.append(_geo_to_dict(item))

        # GDELT geo-tagged breaking news
        for item in fetch_gdelt_geojson(limit=30):
            all_items.append(_geo_to_dict(item))

        return all_items


def _geo_to_dict(item: GeoItem) -> dict:
    return {
        "id": f"gn-{hash(item.url or item.title) & 0xffffffff:08x}",
        "title": item.title,
        "url": item.url or None,
        "score": item.score,
        "source": item.source,
        "fetched_at": item.fetched_at,
        "topics": item.topics,
        # Geo fields (extra, used by frequency analyzer and geolocate source)
        "lat": item.lat,
        "lon": item.lon,
        "country": item.country,
        "country_code": item.country_code,
    }
