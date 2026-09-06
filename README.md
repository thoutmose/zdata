<p align="right"><strong>🇬🇧 English</strong> · <a href="README.fr.md">🇫🇷 Français</a></p>

# ZEvent Dataviz

![Python](https://img.shields.io/badge/python-3.14-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/streamlit-app-FF4B4B?logo=streamlit&logoColor=white)
![uv](https://img.shields.io/badge/managed%20with-uv-DE5FE9)
![Ruff](https://img.shields.io/badge/lint%20%2B%20format-ruff-D7FF64)
![ty](https://img.shields.io/badge/type--checked-ty-1E90FF)
![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL-4169E1?logo=postgresql&logoColor=white)

Data-modeling dashboards for the ZEvent charity gaming
marathon — donations, streamers, games, chat, and community, each on its own
Streamlit page, backed by a pooled PostgreSQL connection (via PgBouncer) with
a mock-data fallback for local development. A sidebar-wide set of filters
(date range, streamers, chatters, entity search, EN/FR language) applies
consistently across every page — see [Global filters](#global-filters).

## Table of contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Pages](#pages)
- [Global filters](#global-filters)
- [Development](#development)
- [Security](#security)
- [Data & methodology](#data--methodology)
- [Coding philosophy](#coding-philosophy)

## Overview

The app is a small set of focused Streamlit pages, one per data-modeling
topic, reading from a shared PostgreSQL database through a typed
repository layer. Until real database credentials are supplied, every page
runs end to end against deterministic sample data, so the whole app can be
developed, reviewed, and demoed offline.

## Architecture

```mermaid
flowchart LR
    Browser["Browser (visitor)"] -- HTTPS / WSS --> Proxy["Reverse proxy\n(TLS termination, deploy-time)"]
    Proxy --> App["Streamlit server\napp/🏠_Home.py + app/pages/*"]
    App --> Repo["app/data/repository.py\n(typed data-access API)"]
    Repo -- no DB credentials --> Mock["app/data/mock.py\n(deterministic sample data)"]
    Repo -- DB credentials set --> DB[("PostgreSQL\n(pooled connections)")]
    App --> Config["app/core/config.py\n(.env / environment variables)"]
    App --> Logging["app/core/logging_config.py\n(colorlog, per-session id)"]
```

The repository layer is the only thing that changes when the real database
is wired up — pages never talk to the database or to the mock data directly.

## Project structure

```
zevent-dataviz/
├── app/
│   ├── 🏠_Home.py                 # Streamlit entrypoint: sidebar filters/search/language render here
│   ├── pages/                     # One page per data-modeling topic (see Pages below)
│   │   ├── 1_📈_Donations.py
│   │   ├── 2_🎙️_Streamers.py
│   │   ├── 3_🎮_Games.py
│   │   ├── 4_🎯_Donation_Goals.py
│   │   ├── 5_💬_Live_Chat.py
│   │   ├── 6_👥_Community.py
│   │   ├── 7_🏆_Donation_Tracker.py
│   │   ├── 8_🗣️_Chatters.py
│   │   ├── 9_📺_Activity.py
│   │   ├── 10_ℹ️_About.py
│   │   ├── 11_🔎_Chat_Messages.py
│   │   ├── 12_🥇_Leaderboard.py
│   │   ├── 13_🧠_Chat_Intelligence.py
│   │   └── 14_🔬_Chat_ML_Lab.py
│   ├── core/
│   │   ├── config.py             # Settings: env vars / .env, never hardcoded secrets
│   │   ├── logging_config.py     # logging.yml-driven setup, per-session correlation id
│   │   ├── db.py                 # Pooled SQLAlchemy engine (st.cache_resource)
│   │   ├── tz.py                 # Europe/Paris timezone helpers (naive wall-clock convention)
│   │   ├── i18n.py               # EN/FR language switcher (t(), language_selector())
│   │   └── translations.py       # The EN/FR string catalog
│   ├── data/
│   │   ├── mock.py               # Deterministic sample data
│   │   ├── repository.py         # Typed data-access API (mock vs. Postgres)
│   │   ├── goal_progress.py      # Shared goal start/complete/duration computation
│   │   ├── bot_heuristic.py      # Heuristic likely-bot chatter filter
│   │   ├── anonymize.py          # Chatter-identity anonymization helper
│   │   ├── emote_cdn.py          # Twitch emote image URL resolution
│   │   ├── external_donations.py # Non-Twitch (external) donation sources
│   │   ├── chat_nlp.py           # Lightweight, dependency-free chat text analysis
│   │   ├── chat_lexicons.py      # Curated hostile/positive/hype word lists (Chat Intelligence)
│   │   └── chat_ml.py            # Real ML: sklearn clustering/outlier/forecast + transformers (Chat ML Lab)
│   └── components/
│       ├── theme.py              # Chart palette & shared Plotly layout
│       ├── chrome.py             # Page header, data-source banner, language selector wiring
│       ├── filters.py            # Global date-range/streamer/chatter filter widgets + appliers
│       ├── search.py             # Global entity search box (jumps to the matching page)
│       └── network_graph.py      # Force-directed network graph (networkx + Plotly)
├── tests/                        # pytest suite
├── .streamlit/config.toml        # Server & theme configuration
├── .env.example                  # Documented environment variables (no secrets)
├── logging.yml                   # Logging profiles (development / production)
└── .claude/skills/karpathy-guidelines/SKILL.md  # Coding philosophy this repo holds itself to
```

## Getting started

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14 (uv installs the
interpreter automatically).

```bash
git clone <this-repo>
cd zevent-dataviz
uv sync                      # installs dependencies into .venv
cp .env.example .env         # fill in DB credentials once you have them
uv run streamlit run app/🏠_Home.py
```

Without database credentials in `.env`, the app runs immediately against
sample data — every page works out of the box.

## Configuration

All configuration is environment variables (or a `.env` file), never
hardcoded. See [`.env.example`](.env.example) for the full list; the
database fields:

| Variable | Description | Default |
|---|---|---|
| `DB_HOST` | PostgreSQL/PgBouncer host | _unset → mock data_ |
| `DB_PORT` | PostgreSQL/PgBouncer port | `5432` |
| `DB_NAME` | Database name | _unset_ |
| `DB_USER` | Database user (a **read-only** role is strongly recommended) | _unset_ |
| `DB_PASSWORD` | Database password | _unset_ |
| `DB_POOL_SIZE` | Base connection pool size | `5` |
| `DB_MAX_OVERFLOW` | Extra connections allowed under load | `10` |
| `DB_STATEMENT_TIMEOUT_MS` | Max time a single query may hold a connection | `15000` |
| `APP_ENV` | `development` or `production` — also selects the [`logging.yml`](logging.yml) profile | `development` |

## Pages

Every page has a language switcher (EN/FR) in the sidebar, translating all UI chrome — see `app/core/translations.py`.

| Page | Topic |
|---|---|
| 📈 Donations | Cumulative donations, a top-3 podium, hourly pace, this year vs. past ZEvent editions, an animated donation-race by channel, donation-spike moments, event-phase split, leaderboard movers, data-quality check |
| 🎙️ Streamers | Rank by donations/engagement/audience; a donation-efficiency-colored correlation scatter; compare up to 4 streamers on a percentile radar chart, chatter-loyalty mix, and hourly viewer pattern; top chatters across the selected streamers |
| 🎮 Games | Categories played, event-wide concurrent viewership over time, recent stream sessions, and a stream-title leaderboard by messages/donations |
| 🎯 Donation Goals | The milestone goals ("objectifs") streamers set for donations, by category and by streamer, an adjustable-cutoff amount histogram, and an ambition-vs-reality chart (goal coverage %) |
| 💬 Live Chat | Chat message volume and engagement rate over time, an animated message-count race by channel, chat-spike moments, a channel×hour activity heatmap, busiest channels, top emotes |
| 👥 Community | Chatter loyalty and account-age mix, cumulative chatter growth, an hour-by-hour force-directed network graph of shared audiences, most active chatters, shared-audience channel pairs |
| 🏆 Donation Tracker | Tracks each "donation"-type goal's start/completion/duration — globally across all streamers, and per streamer, with a Gantt-style timeline |
| 🗣️ Chatters | Chatters page mirroring Streamers: rank by activity/breadth/loyalty, drill into one chatter's per-channel breakdown |
| 📺 Activity | Per-streamer stream title/category timeline — when and how often a streamer changed what they were playing |
| 🔎 Chat Messages | Browse and full-text search individual chat messages, with real chatter/channel identity shown |
| 🥇 Leaderboard | Consolidated top-3 podiums and full rankings pulling together the app's various per-entity leaderboards |
| 🧠 Chat Intelligence | Lightweight, dependency-free lexicon/heuristic analysis of live chat — hostility/positivity word-lists, hype-emote trends, copy-paste detection, toxicity examples with real chatter/channel identity |
| 🔬 Chat ML Lab | Real trained ML over chat and streamer/chatter data: message-topic clustering (KMeans + TF-IDF), streamer/chatter behavioral clustering with a 2D PCA scatter, Isolation Forest outlier detection, pretrained-transformer sentiment/toxicity classification compared against the lexicon heuristic, and a Random Forest donation-forecasting model that predicts each streamer's eventual final total from a mid-event snapshot |
| ℹ️ About | What ZEvent is, what this dashboard does, and how its data pipeline works |

The real warehouse (`raw`/`stg`/`int`/`marts` schemas, dbt-modeled) has no
"team" dimension for streamers, so streamers are ranked individually rather
than grouped, and no sentiment/emotion data at all — the chat engagement
rate (messages/min/100 viewers) is the closest real proxy for "enthusiasm."
It's fed by **two independent pipelines**: a donations pipeline
(ZEvent's own site — `mart_donations__*`, `mart_event__*`, `mart_donation_goals__*`)
and a Twitch metadata/chat pipeline (`mart_streams__*`, `mart_chat__*`,
`mart_chatters__*`, `mart_community__*`). The donations pipeline's `game`
field isn't populated pre-event, so the Games page deliberately reads
categories from the Twitch pipeline instead. Chat usernames aren't in any
`raw.chat_messages_*` table this role can read, but ARE recoverable via
`int.int_chat__chatter_activity.chatter`, joined by `chatter_id`. See
`app/data/repository.py::PostgresDataSource` for the extension point.

## Global filters

Rendered once, in the sidebar (`app/🏠_Home.py`, via `app/components/filters.py`
and `app/components/search.py`) — Streamlit re-runs that entrypoint before every
page, so a single render there puts the filters above the nav links everywhere:

- **Date range** — a slider bounded by the event's own timestamps (not
  wall-clock "now", so it doesn't silently break on mock data or after the
  event ends). Every page's data-fetching either takes `(start, end)`
  straight from this range or narrows an already-fetched frame with
  `apply_global_date_filter`.
- **Streamers** / **Chatters** — sidebar multiselects narrowing every page's
  data to the selected entities (`apply_global_streamer_filter` /
  `apply_global_chatter_filter`); left empty, every page shows all of them.
- **Search** — a sidebar box that finds a streamer/chatter/channel by name and
  jumps to the page that covers it, pre-filling that page's own local
  search/filter widget (`consume_search_query()`).
- **Language (EN/FR)** — `language_selector()`, backed by `app/core/translations.py`;
  every user-facing string on every page goes through `t()`.

## Development

```bash
uv run ruff format .        # formatting
uv run ruff check . --fix   # linting (Google-style docstrings enforced)
uv run ty check .           # static type checking
uv run pytest               # tests
```

All four must pass before a change is considered done — see
[`.claude/skills/karpathy-guidelines/SKILL.md`](.claude/skills/karpathy-guidelines/SKILL.md)
for the coding standards this repo holds itself to.

## Security

Designed to eventually run on the public internet, so:

- **Secrets** live only in environment variables / `.env` (gitignored) —
  never in source, never logged. Use a **read-only** database role.
- **SQL injection**: every real-database query uses `sqlalchemy.text()`
  with bound parameters; string-formatted SQL is not used anywhere in this
  codebase.
- **Connection exhaustion**: one pooled, bounded `Engine` is shared by every
  concurrent session (`st.cache_resource`), with `pool_pre_ping` and
  `pool_recycle`. The database sits behind **PgBouncer**, so `statement_timeout`
  is applied with a `SET` on every pool checkout rather than as a startup
  parameter — PgBouncer only forwards a fixed allowlist of startup parameters
  and rejects unknown ones outright, and re-applying it per checkout is also
  correct under PgBouncer's transaction-pooling mode, where a logical session
  can be handed a different backend connection between transactions.
- **Load on the database**: query results are cached server-side for a short
  TTL (`st.cache_data`), so many concurrent visitors share one query instead
  of each triggering a fresh round trip.
- **CSRF / cross-origin**: `server.enableXsrfProtection` and
  `server.enableCORS` are on; before deploying publicly, also set
  `server.allowedHosts` to the real domain(s) — neither setting alone
  restricts cross-origin WebSocket access.
- **Error surface**: `client.showErrorDetails` is off, so a production
  visitor sees a generic error, not an internal stack trace.
- **Logging**: structured, timestamped, tagged with a per-session id (so
  concurrent users' logs can be told apart), split by level into rotated,
  gzip-compressed files under `logging/` (config in [`logging.yml`](logging.yml)) —
  never logs credentials or full connection strings.

## Data & methodology

Until real credentials are configured, all figures come from
`app/data/mock.py` — clearly deterministic sample data, flagged with a
visible banner on every page.

With the real database connected: figures reflect the live event pipeline as
it stands, which may mean mostly zeros/empty charts before ZEvent actually
starts — that's accurate, not a bug. Two caveats worth knowing:

- **Donation-goal amounts are not reliable "real money" figures.** Streamers
  set their own goal amounts, and jokes in the hundreds of millions of euros
  exist alongside genuine ones. The Donation Goals page charts counts, not
  summed amounts, for exactly this reason.
- **No "team" dimension exists** in the warehouse — the Streamers page ranks
  individuals only.

## Coding philosophy

See [`.claude/skills/karpathy-guidelines/SKILL.md`](.claude/skills/karpathy-guidelines/SKILL.md):
readable over clever, minimal indirection, no speculative generality. AI
assistants are **never** listed as commit co-authors in this repository.
