# neohiro/news — Public Global News Aggregator

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenSource](https://img.shields.io/badge/Public%20Repo-Zero%20User%20Data-success)](README.md)
[![Dependabot](https://img.shields.io/static/v1?label=Dependabot&message=enabled&color=success&logo=dependabot)](.github/dependabot.yml)

**Public global intelligence news feed.** RSS, platform status pages, HackerNews, GitHub Status, and more. Runs as a GitHub Actions cron (hourly) — no server required.

## Body Position

```
   ┌────────────────────────────────────────────────────────────────┐
   │              Body Anatomy — news is the eyes 👁️                 │
   │                                                                │
   │   Outside feeds                                                │
   │     RSS · GitHub status · platform status pages                │
   │     HackerNews · Google News · GDELT                           │
   │              │                                                 │
   │              ▼                                                 │
   │   ┌──────────────┐                                             │
   │   │   news 👁️    │── normalizes, dedups, scores ──►            │
   │   └──────────────┘                                             │
   │              │                                                 │
   │              ▼                                                 │
   │   ┌──────────────┐                                             │
   │   │  data/digest │── hourly cron pushes to neohiro/Brain       │
   │   │   .json      │   which reads it for its Situation object   │
   │   └──────────────┘                                             │
   │                                                                │
   │   news has NO memory of its own. It is the body's EYES:        │
   │   it looks outward, sees what is there, and reports.          │
   │                                                                │
   └────────────────────────────────────────────────────────────────┘
```

> **Privacy contract**: This repo contains **zero user data, zero private data, zero identifying information**. All output is public. Private intelligence (your monitored domains, your breach status, your personalized briefings) lives in [`neohiro/Brain`](https://github.com/neohiro/Brain).

## Dependency graph

```
neohiro/news                          ← YOU ARE HERE (public)
  │ feeds: public RSS + status pages
  │ output: public/feeds/, public/digests/
  │
  ├── feeds to neohiro/Brain ─────────────── (private route)
  │     Brain stores your private intel
  │     Brain feeds Mouth for briefings
  │
  └── feeds to neohiro/network ──────────── (private route)
        Brain enriches with context
        Brain decides who sees what (godadmin / admin / public)

Source inspiration (private repos, learn-only):
  wingman-hub/scripts/tech_signal_harvester.py  → neohiro/news/scripts/fetch.py
  wingman-hub/scripts/scrapling_runner.py       → neohiro/news/src/news/sources/scrapling.py
  wingman-hub/scripts/event_scout.py            → neohiro/news/scripts/event_scout.py
  neohiro/NewsAggregator (standalone app)        → patterns only, not code

Superseded by neohiro/Brain (private):
  wingman-hub/scripts/process_briefing.py       → neohiro/Brain (private)
  wingman-hub/scripts/threat_intel_radar.py     → neohiro/Brain (private)
  wingman-hub/scripts/osint_investigator.py     → neohiro/Brain (private)
```

## Feeds collected

| Source | Type | Update | Notes |
|--------|------|--------|-------|
| GitHub Status | RSS | 15 min | https://www.githubstatus.com/history.rss |
| Cloudflare Status | RSS | 15 min | status.cloudflare.com |
| AWS Health | RSS | 15 min | aws-amazon.com/pages/health |
| HackerNews API | REST | 60 min | Top 30 stories, keyword-filtered |
| Tailscale Status | RSS | 60 min | status.tailscale.com |
| Google News (Serper) | API | 60 min | `SERPER_API_KEY` optional |
| Mastodon (public) | REST | 60 min | No auth, public timelines |
| Bluesky (public) | REST | 60 min | No auth, public feeds |
| crt.sh (CT logs) | HTTPS | 60 min | Domain enumeration, generic |
| transhumanists RSS | RSS | 60 min | Specialized niche feeds |

See [FEEDS.md](FEEDS.md) for full list with URLs and update frequencies.

## Quick start

```bash
# Clone
git clone https://github.com/neohiro/news.git
cd news

# Install (Python 3.12+)
pip install -e .

# Run all sources
python -m news.fetch --all

# Run specific source
python -m news.fetch --source rss --source hn

# Output to public/feeds/
python -m news.fetch --all --output public/feeds/

# Local test (dry run)
python -m news.fetch --source test --dry-run

# Run tests
pytest tests/
```

## Run without installing (standalone)

```bash
# Just download and run — no pip install
curl -fsSL https://raw.githubusercontent.com/neohiro/news/main/scripts/fetch.py | python3 - --all
```

## GitHub Actions

The cron workflow runs every hour. It fetches all sources and commits the results to `public/`. No secrets required for the RSS sources. Optional secrets:

- `SERPER_API_KEY` — Serper.dev Google News API (free tier: 2,500 queries/month)
- `GITHUB_TOKEN` — higher rate limit for GitHub API

## Output format

Every output file is JSON:

```json
{
  "version": 1,
  "source": "hackernews",
  "fetched_at": "2026-08-29T14:00:00Z",
  "items": [
    {
      "id": "39482341",
      "title": "...",
      "url": "https://...",
      "score": 342,
      "source": "HackerNews",
      "fetched_at": "2026-08-29T14:00:00Z"
    }
  ]
}
```

Files are written to `public/feeds/<source>/<YYYY-MM-DD>.json`. The latest snapshot is always at `public/feeds/<source>/latest.json`.

## Architecture

```
scripts/fetch.py           CLI entry, orchestrates pipeline
src/news/
  sources/
    rss.py                 feedparser-based RSS/Atom fetcher
    github_status.py        GitHub public event stream
    hackernews.py           HN Firebase API + keyword filter
    serper.py              Serper.dev Google News API (optional)
    google_news.py         Google News RSS + GDELT geo-tagged breaking news
    geolocate.py           IP geolocation (ip-api.com, ipinfo.io) via neohiro/apis
    dns_whois.py           DNS + RDAP WHOIS via neohiro/apis public connector
    mastodon.py             Mastodon public REST API
    bluesky.py              Bluesky AT Protocol public API
    transhumanists.py       Pulls specialized RSS from github/transhumanists
    certwatch.py            crt.sh certificate transparency (generic domains only)
  normalizer.py             Deduplicate, score-rank, tag by topic
  frequency.py             Frequency analysis + geo centroid + break detection
  output.py                 Write JSON to public/feeds/
  cli.py                    argparse + dry-run + JSON output modes
tests/
  test_sources.py           Mocked HTTP tests per source
  test_normalizer.py        Deduplication + scoring tests
  test_frequency.py         Frequency + break detection + region grouping
  test_output.py            File write tests
```

## Topics tagged

Each item is tagged with one or more topics from:

```
ai llm agent security vulnerability cyberprivacy transhumanism
space astronomy f1 racing neuro privacy zero-day quantum
open-source devops infrastructure cloud geopolitics science health climate finance
```

Used by the normalizer for deduplication and scoring, and by `frequency.py` to build per-topic frequency digests.

## Frequency analysis (breaking news detection)

The `frequency.py` module answers:

- **How often does a topic come up worldwide?** → `topic_frequency()` groups by topic, counts, shows region distribution, computes geo centroid
- **Which regions are active?** → `region_frequency()` maps country → count + top topics
- **What's breaking right now?** → `detect_breaks()` filters items within the last 60 minutes that have geo data or high score

Output goes to `public/feeds/digest/latest.json` — consumed by `neohiro/Brain` for briefings.

## neohiro/apis public connector

`neohiro/news` uses `neohiro/apis` as a **public connector** for services that would otherwise require per-user keys or expose the network topology of the caller:

| Feature | Public service | Via neohiro/apis? |
|---------|---------------|-------------------|
| IP geolocation | ip-api.com, ipinfo.io | Falls back directly if unconfigured |
| DNS | Cloudflare 1.1.1.1 | Optional, direct fallback always works |
| WHOIS | publicrdap.org | Optional, direct fallback always works |
| Reverse geocode | Nominatim OSM | Direct, always works |

Set `NEWS_APIS_BASE=https://api.neohiro.io` to route through `neohiro/apis`. Without it, all sources work directly from public APIs.

## Contributing

1. Add a new source in `src/news/sources/<name>.py` following the `BaseSource` interface
2. Register it in `src/news/sources/__init__.py`
3. Add tests in `tests/test_sources.py`
4. Update `FEEDS.md` with the new feed
5. Open a PR

## License

MIT — see [LICENSE](LICENSE). All scripts here are FrenzyPenguin Media Open Source.

## See also

- [`neohiro/Brain`](https://github.com/neohiro/Brain) — private intelligence hub (receives this repo's feeds)
- [`neohiro/network`](https://github.com/neohiro/network) — device health + telemetry
- [`neohiro/dashboard`](https://github.com/neohiro/dashboard) — live operations view
- [`neohiro/apis`](https://github.com/neohiro/apis) — API library consumed by Brain
- [`neohiro/transhumanists`](https://github.com/neohiro/transhumanists) — specialized RSS feeds
