# src/news/cli.py
# CLI entry: python -m news.cli --all

import argparse
import sys
from pathlib import Path

from .sources import SOURCES, BaseSource, NewsItem
from .normalizer import normalize
from .output import write_feeds, write_combined


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="news",
        description="neohiro/news — public news aggregator. Zero user data.",
    )
    parser.add_argument(
        "--source",
        action="append",
        choices=list(SOURCES.keys()) + ["all"],
        help=f"Source(s) to fetch. Available: {', '.join(sorted(SOURCES.keys()))}",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all sources",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("public/feeds"),
        help="Output directory (default: public/feeds)",
    )
    parser.add_argument(
        "--combined",
        action="store_true",
        help="Also write combined/latest.json with all items",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print fetched items to stdout, do not write files",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print fetched items as JSON to stdout (used by tests)",
    )
    args = parser.parse_args()

    sources_to_run: list[str]
    if args.all:
        sources_to_run = list(SOURCES.keys())
    elif args.source:
        sources_to_run = [s for s in args.source if s != "all"]
    else:
        sources_to_run = list(SOURCES.keys())

    all_items = []
    summary: dict[str, int] = {}
    for name in sources_to_run:
        cls = SOURCES.get(name)
        if not cls:
            print(f"[news] unknown source: {name}", file=sys.stderr)
            continue
        source = cls()
        try:
            raw = source.fetch()
        except Exception as e:
            print(f"[news] {name} failed: {e}", file=sys.stderr)
            raw = []
        # Normalize: some sources return dicts, convert to NewsItem
        items = []
        for r in raw:
            if isinstance(r, dict):
                items.append(NewsItem(
                    id=str(r.get("id", "")),
                    title=str(r.get("title", "")),
                    url=r.get("url") or None,
                    score=int(r.get("score") or 0),
                    source=str(r.get("source", name)),
                    fetched_at=str(r.get("fetched_at", "")),
                    topics=list(r.get("topics") or []),
                ))
            else:
                items.append(r)
        summary[name] = len(items)
        if args.dry_run or args.json:
            for it in items:
                print(_item_json(it))
        if not args.dry_run:
            write_feeds(items, name, args.output)
        all_items.extend(items)

    if args.combined and not args.dry_run:
        write_combined(normalize(all_items), args.output)

    if args.dry_run or args.json:
        return 0

    print(f"[news] summary: {summary}")
    print(f"[news] wrote {len(all_items)} items to {args.output}")
    return 0


def _item_json(item) -> str:
    import json
    return json.dumps({
        "id": item.id,
        "title": item.title,
        "url": item.url,
        "source": item.source,
        "score": item.score,
        "topics": item.topics,
    }, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())
