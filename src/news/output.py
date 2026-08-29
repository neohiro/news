# src/news/output.py
# Write normalized news items to JSON files in public/feeds/.
# All output is public. Zero user data.

import json
from datetime import datetime, timezone
from pathlib import Path

from .sources import NewsItem


def write_feeds(items: list[NewsItem], source: str, out_dir: str | Path) -> Path | None:
    """Write items to out_dir/<source>/<YYYY-MM-DD>.json and latest.json."""
    out_dir = Path(out_dir)
    if not items and not out_dir.exists():
        return None

    source_dir = out_dir / source
    source_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snapshot = {
        "version": 1,
        "source": source,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": [_item_to_dict(i) for i in items],
    }

    daily_path = source_dir / f"{today}.json"
    latest_path = source_dir / "latest.json"

    for path in (daily_path, latest_path):
        path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))

    return latest_path


def write_combined(items: list[NewsItem], out_dir: str | Path) -> Path | None:
    """Write all items to out_dir/combined/latest.json."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    combined = {
        "version": 1,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": [_item_to_dict(i) for i in items],
    }
    path = out_dir / "combined" / "latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(combined, indent=2, ensure_ascii=False))
    return path


def _item_to_dict(item: NewsItem) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "url": item.url,
        "score": item.score,
        "source": item.source,
        "fetched_at": item.fetched_at,
        "topics": item.topics,
    }
