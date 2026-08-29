# SUPERSEDES.md — What this repo supersedes

This document maps private scripts in `wingman-hub` to their public equivalents in `neohiro/news`.
The private scripts in wingman-hub are NOT deleted — they are annotated with a reference
to this repo and remain available for migration/history purposes.

## Principle

- **Public news aggregation logic** → `neohiro/news` (this repo, public)
- **Private user-specific intelligence** → `neohiro/Brain` (private)
- **User memory and briefings** → `neohiro/Brain` (private)
- **Pattern reference only** (not code copy) → noted below

## Superseded scripts (from `neohiro/wingman-hub/scripts/`)

### `tech_signal_harvester.py` → `src/news/sources/serper.py` + `src/news/sources/hackernews.py`

| wingman-hub (private) | neohiro/news (public) |
|-----------------------|----------------------|
| Serper API key required | Serper optional (`SERPER_API_KEY`) |
| Keyword filter for personal interests | Generic tech/AI/security keywords |
| Merged with private briefing data | Outputs to `public/feeds/` only |
| Formats for WhatsApp | Outputs JSON + markdown |

**What changed**: Removed personal keyword interests (transhumanism, F1, etc. are still included
as generic public tech topics). Removed WhatsApp formatting. Removed integration with
`process_briefing.py`. Added generic keywords that make sense for any user.

### `scrapling_runner.py` → `src/news/sources/scrapling.py`

| wingman-hub (private) | neohiro/news (public) |
|-----------------------|----------------------|
| Accepts arbitrary URLs | Reads from feed registry only |
| Returns raw content | Normalizes to standard JSON |
| Fallback with full UA spoofing | Simplified fallback (requests only) |
| No output format contract | Structured output in `public/feeds/` |

**What changed**: Removed user-supplied URL injection (security boundary). Removed scrapling
dependency (optional install). Simplified to RSS-only for now, with scrapling as optional
enhancement.

### `event_scout.py` → `src/news/sources/hackernews.py` + `src/news/sources/rss.py`

| wingman-hub (private) | neohiro/news (public) |
|-----------------------|----------------------|
| HN + Serper + web scrape | RSS + HN + Serper (public sources) |
| Personalized scoring | Generic relevance scoring |
| Writes to `wingman-hub/data/` | Writes to `public/feeds/` |

## NOT superseded (remain private in `neohiro/Brain`)

These scripts contain user-specific logic, personal data, breach results, or private
intelligence. They are explicitly NOT moved to `neohiro/news`.

| Private script | Reason | Goes to |
|----------------|--------|---------|
| `process_briefing.py` | Personalized briefings with user context | `neohiro/Brain` |
| `process_whatsapp.py` | WhatsApp message processing with contacts | `neohiro/Brain` |
| `process_strangers.py` | Stranger conversation processing | `neohiro/Brain` |
| `threat_intel_radar.py` | Monitors private domains + emails (k-anonymity) | `neohiro/Brain` |
| `osint_investigator.py` | User-specific OSINT queries | `neohiro/Brain` |
| `learn_memory.py` | Writes to wingman-hub memory store | `neohiro/Brain` |
| `weekly_user_profiler.py` | Personal profile construction | `neohiro/Brain` |
| `self_improvement.py` | Evaluates user's opencode sessions | `neohiro/Brain` |
| `dead_letter_handler.py` | Routes failed private workflows | `neohiro/Brain` |
| `scan_open_items.py` | Scans user's open GitHub issues/PRs | `neohiro/Brain` |
| `post_conversation_analyzer.py` | Analyzes user's chat history | `neohiro/Brain` |
| `llm_utils.py` | Calls LLM with user context | `neohiro/Brain` |

## Reference: `neohiro/NewsAggregator` (standalone app)

The `neohiro/NewsAggregator` repo is a **standalone desktop application** for end users.
It is NOT superseded by `neohiro/news`. They coexist:

- `neohiro/NewsAggregator` — GUI app, Windows/Linux/macOS binary, for end users
- `neohiro/news` — CLI/serverless, GitHub Actions cron, for developers and Brain

Patterns learned from `NewsAggregator`:
- Search indexing (not copied)
- RSS parsing with feedparser (used via pip dependency)
- Cross-platform binary builds via GitHub Actions (reference only)

## Reference: `github.com/neohiro/transhumanists`

The `transhumanists` repo has specialized RSS feeds for niche topics.
`neohiro/news` pulls from `transhumanists` as a data source — it does not supersede it.
`transhumanists` remains the canonical source for those niche feeds.

## Reference: `frenzypenguin-media/_tools/`

The `frenzypenguin-media` repo has tool documentation pages (`.md` files in `_tools/`).
These are documentation only and are NOT superseded. `neohiro/news` does not touch
`frenzypenguin-media` content.

## Migration notes

For each superseded script in wingman-hub:

1. Add a comment at the top: `# SUPERSEDED: see https://github.com/neohiro/news`
2. Keep the script in wingman-hub (do not delete)
3. Update `wingman-hub/scripts/README.md` to document the redirect
4. The Brain will consume `neohiro/news/public/feeds/` instead of running these scripts directly
5. Personal configuration (keywords, domains) moves to `neohiro/Brain` configuration
