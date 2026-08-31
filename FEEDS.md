# neohiro/news — Feed registry

All feeds collected by this repo. Update frequency is the GitHub Actions cron interval.
Feeds marked **[optional]** require an API key set as a GitHub Actions secret.

## RSS / Atom feeds

| Name | URL | Update | Notes |
|------|-----|--------|-------|
| GitHub Status | https://www.githubstatus.com/history.rss | 15 min | Real-time status page RSS |
| Cloudflare Status | https://www.cloudflarestatus.com/history.rss | 15 min | Cloudflare status RSS |
| AWS Health | https://status.aws.amazon.com/rss/all.rss | 15 min | AWS health events RSS |
| Tailscale Status | https://status.tailscale.com/history.rss | 60 min | Tailscale status RSS |
| Google Workspace | https://status.cloud.google.com/incidents.rss | 15 min | GCP status RSS |
| DigitalOcean Status | https://status.digitalocean.com/history.rss | 15 min | DO status RSS |
| Hugging Face Status | https://status.huggingface.co/history.rss | 60 min | HF status RSS |
| OpenAI Status | https://status.openai.com/history.rss | 15 min | OpenAI status RSS |

## REST / API sources (no auth)

| Name | Endpoint | Update | Notes |
|------|----------|--------|-------|
| HackerNews Top | https://hacker-news.firebaseio.com/v0/topstories.json | 60 min | Fetch top 30, filter by keyword |
| HackerNews Item | https://hacker-news.firebaseio.com/v0/item/{id}.json | — | Resolved per story |
| Mastodon Public | https://mastodon.social/api/v1/timelines/public | 60 min | No auth, public only |
| Bluesky Feed | https://public.api.bsky.app/xrpc/app.bsky.feed.getTimeline | 60 min | No auth, public only |
| crt.sh CT logs | https://crt.sh/?q=%.example.com&output=json | 60 min | Generic domain scan, no target-specific |

## API sources **[optional]**

| Name | API | Update | Secret | Free tier |
|------|-----|--------|--------|-----------|
| Serper Google News | https://google.serper.dev/news | 60 min | `SERPER_API_KEY` | 2,500/mo |
| HackerNews Algolia | https://hn.algolia.com/api/v1/search | 60 min | None | Unlimited |

## Google News RSS (topic-based, no auth)

10 specialized topics fetched in parallel. RSS only, no API key:

| Topic | What it covers |
|-------|---------------|
| `world` | Top world stories |
| `technology` | Tech industry news |
| `business` | Markets, finance, economy |
| `science` | Scientific breakthroughs |
| `health` | Health and medicine |
| `sports` | Sports news |
| `entertainment` | Arts, films, music |
| `ai` | AI / ML focused |
| `cybersecurity` | Sec research, breaches, vulns |
| `climate` | Climate, environment |

## GDELT (geo-tagged breaking news, no key)

| Source | What it provides | URL |
|--------|------------------|-----|
| GDELT Article API | Article list with social image counts | `https://api.gdeltproject.org/api/v2/doc/doc` |
| GDELT GeoJSON (15-min rolling) | Breaking news with lat/lon | `https://data.gdeltproject.org/internal/geojson/LAST15MIN.geojson` |

GDELT provides GPS coordinates for global news events. Used by `frequency.py` to compute topic centroids and country distribution.

## Geolocation / DNS / WHOIS (via neohiro/apis public connector)

Free public APIs, no auth, no user data. All return public information only:

| Service | Endpoint | Free provider | Use |
|---------|----------|---------------|-----|
| IP geolocation | `https://api.neohiro.io/api/ip/<ip>` | neohiro/apis → ip-api.com → ipinfo.io | Where is this IP? |
| Reverse geocoding | `https://nominatim.openstreetmap.org/reverse` | OpenStreetMap Nominatim | Country/city from lat/lon |
| DNS lookup | `https://api.neohiro.io/api/dns/<domain>` | neohiro/apis → Cloudflare 1.1.1.1 | A/AAAA/MX/TXT/NS records |
| WHOIS / RDAP | `https://api.neohiro.io/api/whois/<domain>` | publicrdap.org | Domain registration data |

If `NEWS_APIS_BASE` env var is set, neohiro/apis is used first; otherwise direct fallbacks are used.

## Transhumanists feeds (from `github.com/neohiro/transhumanists`)

Pulled hourly from the transhumanists repo's RSS sources. See [transhumanists/README](https://github.com/neohiro/transhumanists).

## Local dev

Set `NEWS_FETCH_INTERVAL` env to override update frequency in tests.

## Adding a new feed

1. Add URL + metadata to this table
2. Add source module in `src/news/sources/<name>.py`
3. Register in `src/news/sources/__init__.py`
4. Add tests with mocked responses
5. Update `SUPERSEDES.md` if it supersedes a wingman-hub script
