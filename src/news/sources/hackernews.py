# src/news/sources/hackernews.py
# HackerNews top stories via Firebase API.
# No auth, no user data, public.

import json
from urllib.request import Request, urlopen

from . import BaseSource, NewsItem, register_source


KEYWORDS = [
    "ai", "llm", "agent", "security", "vulnerability", "privacy",
    "open-source", "open source", "foss", "linux", "kubernetes",
    "ransomware", "exploit", "zero-day", "0day", "ransom", "breach",
    "ransomware", "ransom", "ransom", "exploit", "ransom",
]


@register_source
class HackerNewsSource(BaseSource):
    name = "hackernews"

    def fetch(self) -> list[NewsItem]:
        ids = self._fetch_top_ids(limit=30)
        items: list[NewsItem] = []
        for story_id in ids:
            try:
                item = self._fetch_item(story_id)
            except Exception:
                continue
            if item is None:
                continue
            items.append(item)
        return items

    def _fetch_top_ids(self, limit: int = 30) -> list[int]:
        url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        req = Request(url, headers={"User-Agent": "neohiro-news/1.0"})
        with urlopen(req, timeout=self.http_timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [int(s) for s in data[:limit] if isinstance(s, int)]

    def _fetch_item(self, story_id: int) -> NewsItem | None:
        url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        req = Request(url, headers={"User-Agent": "neohiro-news/1.0"})
        with urlopen(req, timeout=self.http_timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not isinstance(data, dict):
            return None
        if data.get("deleted") or data.get("dead"):
            return None
        title = data.get("title", "")
        if not title:
            return None
        score = int(data.get("score", 0))
        link = data.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
        is_relevant = any(kw in title.lower() for kw in KEYWORDS) or score >= 200
        if not is_relevant:
            return None
        return NewsItem(
            id=f"hn-{story_id}",
            title=title,
            url=link,
            score=score,
            source="HackerNews",
            topics=self._detect_topics(title),
            raw={"by": data.get("by"), "type": data.get("type")},
        )

    def _detect_topics(self, title: str) -> list[str]:
        t = title.lower()
        topics = []
        if any(k in t for k in ["ai ", "llm", "gpt", "claude", "agent"]):
            topics.append("ai")
        if any(k in t for k in ["security", "vuln", "exploit", "cve-", "ransom", "breach"]):
            topics.append("security")
        if any(k in t for k in ["privacy", "gdpr"]):
            topics.append("privacy")
        if any(k in t for k in ["open source", "foss", "github"]):
            topics.append("open-source")
        if any(k in t for k in ["linux", "kernel"]):
            topics.append("linux")
        if any(k in t for k in ["cloud", "aws", "azure", "gcp"]):
            topics.append("cloud")
        if any(k in t for k in ["zero-day", "0day"]):
            topics.append("zero-day")
        return topics
