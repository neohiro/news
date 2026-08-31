# src/news/sources/github_status.py
# GitHub public status via the public history.rss feed (Atom/RSS 2.0).
# No auth, no user data, no API rate limit.

import re
import time
from urllib.request import Request, urlopen

from . import BaseSource, NewsItem, register_source


@register_source
class GitHubStatusSource(BaseSource):
    name = "github_status"

    def __init__(self, http_timeout: int = 15):
        super().__init__(http_timeout)
        self.url = "https://www.githubstatus.com/history.rss"

    def fetch(self) -> list[NewsItem]:
        items: list[NewsItem] = []
        req = Request(
            self.url,
            headers={"User-Agent": "neohiro-news/1.0",
                     "Accept": "application/rss+xml, application/atom+xml"},
        )
        try:
            resp = urlopen(req, timeout=self.http_timeout)
            data = resp.read(8192).decode("utf-8", errors="replace")
        except Exception:
            return items

        for m in re.finditer(r"<item\b[^>]*>(.*?)</item>", data, re.DOTALL | re.IGNORECASE):
            block = m.group(1)
            title_m = re.search(r"<title[^>]*>(.*?)</title>", block, re.DOTALL)
            link_m = re.search(r"<link[^>]*>(.*?)</link>", block, re.DOTALL)
            date_m = re.search(r"<pubDate>(.*?)</pubDate>", block, re.DOTALL)
            title = (title_m.group(1) if title_m else "").strip()
            link = (link_m.group(1) if link_m else "").strip()
            if not title:
                continue
            items.append(NewsItem(
                id=f"githubstatus-{int(time.time() * 1000)}-{len(items)}",
                title=title,
                url=link or None,
                source="GitHub Status",
                topics=["infrastructure", "devops"],
                raw={"pubDate": (date_m.group(1) if date_m else "").strip()},
            ))
            if len(items) >= 10:
                break
        return items
