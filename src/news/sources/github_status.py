# src/news/sources/github_status.py
# GitHub public status via the public event stream.
# No auth, no user data, no API rate limit.

import json
import time
from urllib.request import Request, urlopen

from . import BaseSource, NewsItem, register_source


@register_source
class GitHubStatusSource(BaseSource):
    name = "github_status"

    def __init__(self, http_timeout: int = 15):
        super().__init__(http_timeout)
        self.url = "https://www.githubstatus.com/../event-stream"

    def fetch(self) -> list[NewsItem]:
        items: list[NewsItem] = []
        # Read up to 4KB of the event stream; truncate to avoid hanging
        req = Request(self.url, headers={"User-Agent": "neohiro-news/1.0", "Accept": "text/event-stream"})
        try:
            resp = urlopen(req, timeout=self.http_timeout)
            data = resp.read(4096).decode("utf-8", errors="replace")
        except Exception:
            return items

        for line in data.splitlines():
            if not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            title = event.get("title", "")
            url = event.get("url", "") or ""
            if not title:
                continue
            items.append(NewsItem(
                id=f"githubstatus-{int(time.time() * 1000)}-{len(items)}",
                title=title,
                url=url or None,
                source="GitHub Status",
                topics=["infrastructure", "devops"],
                raw={"status": event.get("status"), "affected": event.get("affected")},
            ))
        return items
