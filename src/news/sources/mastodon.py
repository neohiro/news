# src/news/sources/mastodon.py
# Mastodon public timeline. No auth. Zero user data.
# Only fetches the federated public timeline, not user-specific feeds.

import json
from urllib.request import Request, urlopen

from . import BaseSource, NewsItem, register_source


@register_source
class MastodonSource(BaseSource):
    name = "mastodon"

    def __init__(self, http_timeout: int = 10):
        super().__init__(http_timeout)
        self.instance = "https://mastodon.social"

    def fetch(self) -> list[NewsItem]:
        url = f"{self.instance}/api/v1/timelines/public?limit=20"
        req = Request(url, headers={"User-Agent": "neohiro-news/1.0"})
        try:
            with urlopen(req, timeout=self.http_timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        items: list[NewsItem] = []
        for status in data:
            content = status.get("content", "")
            if not content:
                continue
            title = content[:140]
            if "<" in title:
                title = title.split("<", 1)[0]
            title = title.strip()
            if not title:
                continue
            items.append(NewsItem(
                id=f"mstd-{status.get('id', '')}",
                title=title,
                url=status.get("url", ""),
                source=f"Mastodon ({self.instance})",
                topics=self._detect_topics(title),
                raw={"reblogs_count": status.get("reblogs_count", 0)},
            ))
        return items

    def _detect_topics(self, content: str) -> list[str]:
        c = content.lower()
        topics = []
        if any(k in c for k in ["ai ", "llm", "gpt", "claude"]):
            topics.append("ai")
        if any(k in c for k in ["security", "vuln", "exploit"]):
            topics.append("security")
        if any(k in c for k in ["privacy", "gdpr"]):
            topics.append("privacy")
        return topics
