# src/news/sources/__init__.py
# Base source interface + registry

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class NewsItem:
    id: str
    title: str
    url: str | None
    score: int = 0
    source: str = ""
    fetched_at: str = ""
    topics: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.fetched_at:
            self.fetched_at = datetime.now(timezone.utc).isoformat()


class BaseSource(ABC):
    name: str = "base"

    def __init__(self, http_timeout: int = 10):
        self.http_timeout = http_timeout

    @abstractmethod
    def fetch(self) -> list[NewsItem]:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"


SOURCES: dict[str, type[BaseSource]] = {}


def register_source(cls: type[BaseSource]) -> type[BaseSource]:
    SOURCES[cls.name] = cls
    return cls


# ─── Register all sources ─────────────────────────────────────────────────────
# Import all source modules so they self-register
from . import rss           # noqa: E402,F401
from . import hackernews   # noqa: E402,F401
from . import serper       # noqa: E402,F401
from . import github_status  # noqa: E402,F401
from . import mastodon     # noqa: E402,F401
from . import google_news # noqa: E402,F401
from . import geolocate    # noqa: E402,F401
from . import dns_whois    # noqa: E402,F401

__all__ = [
    "BaseSource", "NewsItem", "SOURCES",
    "RSSSource", "HackerNewsSource", "SerperSource",
    "GitHubStatusSource", "MastodonSource",
    "GoogleNewsSource", "GeolocateSource", "DNSSource",
]
