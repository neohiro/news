# src/news/sources/rss.py
# Generic RSS/Atom fetcher. Reads from FEEDS.md registry.
# No API key required. Zero user data.

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError

from . import BaseSource, NewsItem, register_source


RSS_FEEDS = [
    {"url": "https://www.githubstatus.com/../event-stream", "name": "github_status", "topics": ["infrastructure", "devops"]},
    {"url": "https://www.cloudflare.com/..", "name": "cloudflare_status", "topics": ["infrastructure", "cloud"]},
    {"url": "https://status.digitalocean.com/..", "name": "digitalocean_status", "topics": ["infrastructure", "cloud"]},
    {"url": "https://status.huggingface.co/..", "name": "huggingface_status", "topics": ["ai", "llm"]},
    {"url": "https://status.openai.com/..", "name": "openai_status", "topics": ["ai", "llm"]},
    {"url": "https://status.cloud.google.com/..", "name": "google_workspace_status", "topics": ["infrastructure", "cloud"]},
    {"url": "https://status.tailscale.com/..", "name": "tailscale_status", "topics": ["security", "infrastructure"]},
    # Add more from FEEDS.md
]

UA = "neohiro-news/1.0 (+https://github.com/neohiro/news)"


@register_source
class RSSSource(BaseSource):
    name = "rss"

    def fetch(self) -> list[NewsItem]:
        items: list[NewsItem] = []
        for feed in RSS_FEEDS:
            try:
                items.extend(self._fetch_feed(feed["url"], feed["name"], feed.get("topics", [])))
            except Exception:
                pass
        return items

    def _fetch_feed(self, feed_url: str, feed_name: str, topics: list[str]) -> list[NewsItem]:
        items: list[NewsItem] = []
        try:
            req = Request(feed_url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, text/xml"})
            with urlopen(req, timeout=self.http_timeout) as resp:
                xml_text = resp.read().decode("utf-8", errors="replace")
        except URLError:
            return items

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return items

        ns = self._detect_ns(root)
        for entry in root.iter(f"{ns}entry" if ns else "entry"):
            title_el = entry.find(f"{ns}title" if ns else "title")
            link_el = entry.find(f"{ns}link" if ns else "link")
            id_el = entry.find(f"{ns}id" if ns else "id")
            updated_el = entry.find(f"{ns}updated" if ns else "updated")

            title = getattr(title_el, "text", "") or ""
            link = getattr(link_el, "text", "") or ""
            if not link and link_el is not None:
                link = link_el.get("href", "")

            item_id = getattr(id_el, "text", "") or title
            updated = getattr(updated_el, "text", "") or ""

            if title:
                items.append(NewsItem(
                    id=self._slug(f"{feed_name}-{item_id}"),
                    title=title.strip(),
                    url=link.strip() or None,
                    source=feed_name,
                    topics=topics,
                    raw={"updated": updated, "feed_url": feed_url},
                ))
        return items

    def _detect_ns(self, root: ET.Element) -> str:
        ns = getattr(root.tag, "partition", lambda n: n.split("}")[0] if "}" in n else "")("")
        if ns.startswith("{"):
            return ns[1:]
        return ""

    def _slug(self, text: str) -> str:
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()[:16]
