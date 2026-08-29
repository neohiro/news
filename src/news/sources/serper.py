# src/news/sources/serper.py
# Serper.dev Google News API. Optional, requires SERPER_API_KEY.
# No user data; uses generic queries.

import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from . import BaseSource, NewsItem, register_source


GENERIC_QUERIES = [
    "artificial intelligence breakthrough",
    "open source security vulnerability",
    "cybersecurity zero-day exploit",
    "data breach privacy",
    "kubernetes cloud infrastructure",
    "open source LLM release",
]


@register_source
@register_source
class SerperSource(BaseSource):
    name = "serper"

    def __init__(self, http_timeout: int = 10):
        super().__init__(http_timeout)
        self.api_key = os.environ.get("SERPER_API_KEY", "")

    def fetch(self) -> list[NewsItem]:
        if not self.api_key:
            return []
        items: list[NewsItem] = []
        for q in GENERIC_QUERIES:
            try:
                items.extend(self._query(q))
            except Exception:
                continue
        return items

    def _query(self, q: str) -> list[NewsItem]:
        body = json.dumps({"q": q, "hl": "en", "num": 5}).encode("utf-8")
        req = Request(
            "https://google.serper.dev/news",
            data=body,
            headers={
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.http_timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code in (401, 403, 429):
                return []
            raise
        out: list[NewsItem] = []
        for item in data.get("news", [])[:5]:
            title = item.get("title", "").strip()
            link = item.get("link", "").strip()
            if not title or not link:
                continue
            out.append(NewsItem(
                id=f"serper-{hash(link) & 0xffffffff:08x}",
                title=title,
                url=link,
                source=f"Serper ({item.get('source', 'Google News')})",
                topics=self._detect_topics(title),
                raw={"date": item.get("date"), "query": q},
            ))
        return out

    def _detect_topics(self, title: str) -> list[str]:
        t = title.lower()
        topics = []
        if any(k in t for k in ["ai", "llm", "gpt", "claude"]):
            topics.append("ai")
        if any(k in t for k in ["security", "vuln", "exploit"]):
            topics.append("security")
        if any(k in t for k in ["privacy"]):
            topics.append("privacy")
        if any(k in t for k in ["breach"]):
            topics.append("security")
        if any(k in t for k in ["kubernetes", "aws", "azure", "cloud"]):
            topics.append("cloud")
        if any(k in t for k in ["open source"]):
            topics.append("open-source")
        return topics
