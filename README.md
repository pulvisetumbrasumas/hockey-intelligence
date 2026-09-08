# Hockey Intelligence

An open-source NHL hockey intelligence platform: a FastAPI backend with a SQLite
database as the source of truth, a deterministic statistics engine, and a modular
Ollama-powered AI reasoning layer that explains database-verified facts — it never
invents numbers.

## Features

- **Premium cinematic web application** — a dark, glass, ice-accented shell served at
  `/` with a full desktop nav, global search, header scoreboard actions, favorites and
  account profiles (local-first), plus a hero dashboard with a **data-driven countdown**
  to the next season pulled from the NHL schedule API.
- **Player, team, and franchise data** from the NHL public APIs (regular season and
  playoffs), stored locally in SQLite.
- **Deterministic statistics engine** — career/season aggregation and multi-dimensional
  player comparison (offense, defense, puck skill, durability, efficiency). It never
  declares a single "winner". Also provides season and all-time **leaderboards** for
  skater and goalie metrics (with tie handling and min-games guards for rate stats).
- **Living league views** — schedule & scores and live-NHL boards are proxied from the
  NHL schedule endpoint; standings, career/season leaders and player pages are computed
  from the embedded database.
- **Database-grounded AI assistant** — natural-language questions are answered by an
  Ollama model that selects tools; tool results are resolved against the database and
  fed back, so answers quote verified numbers. Includes a `get_league_leaders` tool for
  "who led the league in X" questions.
- **Provider abstraction** — new data sources can be plugged in via `HockeyDataProvider`.
- **Historical awareness** — preserves defunct/relocated franchise identities (e.g.
  Hartford Whalers are not the Carolina Hurricanes); a franchise pages marries each club
  to its identity timeline.

## Quickstart

### Prerequisites

- Python 3.11+ (developed on 3.14)
- [Ollama](https://ollama.com) running locally with a tool-capable model, e.g.
  `ollama pull llama3.2`

### Install and run

```bash
cd hockey-intelligence
pip install -e ".[dev]"

cp .env_sample .env        # then edit as needed
ollama serve                # in a separate terminal

# Create/update the schema via migrations
alembic upgrade head

# Seed the database (10 seasons: 2015-16 through 2024-25, incl. playoffs + bios)
PYTHONPATH=. python scripts/seed.py

# Run the API
PYTHONPATH=. python -m uvicorn app.main:app --port 8000
# or: PYTHONPATH=. python scripts/run.py
```

Interactive docs: http://localhost:8000/docs

### Try it

Open http://localhost:8000 — the cinematic application shell. The **Home** dashboard
shows a countdown to the next season, today's games, a featured player, standings
preview and a league events timeline. Browse **Players**, **Teams**, **Franchises**,
**Standings & leaders**, **Schedule**, **Compare**, **History**, an experimental
**Fantasy** draft-room shell, and the **AI Hockey Analyst** chat. Global search (press
`/`), favorites (☆) and a local profile live in the header.

```bash
# Headless API hits
# Search players/teams/franchises
curl "http://localhost:8000/api/search?q=McDavid"

# Profile + career stats
curl "http://localhost:8000/api/players/8478402"
curl "http://localhost:8000/api/players/8478402/career"

# Season facts (data-driven countdown target) + upcoming events
curl "http://localhost:8000/api/season-facts"
curl "http://localhost:8000/api/events"

# Schedule proxy (today / next / YYYY-MM-DD) — live league games
curl "http://localhost:8000/api/schedule?date=today"

# Standings + tracked seasons
curl "http://localhost:8000/api/standings?season_id=20242025"
curl "http://localhost:8000/api/seasons"

# Leaders (season or career; incl. ties and goalie metrics)
curl "http://localhost:8000/api/stats/leaders/season/20242025?metric=points&stat_type=skater"
curl "http://localhost:8000/api/stats/leaders/career?metric=points_per_game&min_games=30"

# Compare (evidence per dimension, no single winner)
curl -X POST "http://localhost:8000/api/compare/players?player_ids=8478402&player_ids=8478550"

# Database-grounded AI question
curl -X POST http://localhost:8000/api/ai/ask \
  -d '{"question": "How many points did Connor McDavid score in 2024-25, and how did his points-per-game compare to Artemi Panarin?"}'
```

## Architecture

```
app/
├── api/routes/        # HTTP layer (players, teams, platform, statistics, ai)
├── core/config.py     # env-driven settings (pydantic-settings)
├── data/seeder.py     # ingestion pipeline from the NHL provider
├── database/          # async engine, sessions, init_db
├── models/            # SQLAlchemy models (24 tables)
├── providers/         # HockeyDataProvider ABC + NHL implementation
├── schemas/           # API response models
├── services/
│   ├── ai/            # Ollama tool-calling loop + tool resolvers
│   ├── images.py      # deterministic NHL media URL builders
│   ├── media.py       # player->team media lookups from the database
│   └── statistics/    # deterministic calculation engine (incl. leaderboards)
└── static/            # cinematic web application shell served at /
    ├── css/styles.css # design system (tokens, glass, glow, responsive)
    └── js/
        ├── app.js         # router, nav, global search, account/favorites
        └── pages/*.js     # home, players, teams, standings, compare, ai, misc
```

Data flow: `NHL provider → seeder → SQLite (source of truth) → statistics engine
(deterministic) → AI layer (reasons/explains only)`.

See [`docs/architecture.md`](docs/architecture.md) for details.

## AI layer notes

- The model never fabricates IDs or numbers. Tools accept `full_name` (resolved
  against the database) in addition to numeric IDs, and the system prompt forbids
  guessing statistics.
- Default model is `llama3.2:latest`; swap with `OLLAMA_MODEL` in `.env`
  (e.g. `qwen3:4b`). On CPU-only hardware qwen3 is much slower (~3x per tool turn).

## Testing

```bash
python -m pytest tests/ -q     # 31 tests
python -m ruff check .         # lint
```

## Configuration

All settings are environment variables (`.env`). Notable ones:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./hockey_intelligence.db` | Database |
| `OLLAMA_MODEL` | `llama3.2:latest` | AI model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_TIMEOUT` | `420` | Tool-call latency can be high on CPU |
| `OLLAMA_KEEP_ALIVE` | `10m` | Keep model loaded in memory between requests |
| `DATA_SEED_SEASONS` | `20152016,...,20242025` | Default seasons for `scripts/seed.py` |
| `NHL_STATS_API_BASE` | `https://api.nhle.com/stats/rest/en` | NHL stats API |
| `NHL_WEB_API_BASE` | `https://api-web.nhle.com/v1` | NHL web API (bios, schedule) |
| `SCHEDULE_CACHE_TTL` | `120` | Seconds to cache the schedule proxy |
| `SEASON_FACTS_CACHE_TTL` | `21600` | Seconds to cache season countdown facts |
| `COUNTDOWN_TARGET_FALLBACK` | `2026-10-07` | Countdown fallback if the NHL API is unreachable |
| `TRADE_DEADLINE_DATE` / `NHL_DRAFT_DATE` / `ALL_STAR_DATE` | `2027-03-05` / `2027-06-26` / `2027-02-06` | Calendar events |

## Database migrations

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org):

```bash
alembic upgrade head          # apply migrations (creates the full schema on a fresh DB)
alembic revision --autogenerate -m "describe change"   # after editing app/models
alembic upgrade head          # apply the new migration
```

`migrations/env.py` wires Alembic to the async engine and `app.models.metadata`, and
reads `DATABASE_URL` from `.env`. The existing dev database is stamped at head, so the
baseline migration matches it exactly (verified: autogenerate is a no-op and `upgrade
head` reproduces the schema on a fresh DB).

## Status & limitations

- Data is sourced from the NHL's public APIs; review their terms before redistribution.
- Seeded by default: 2015-16 through 2024-25 (regular season + playoffs) for skaters and
  goalies, plus player bios. Add more seasons with
  `PYTHONPATH=. python scripts/seed.py 20052006 20062007` (idempotent; bios are backfilled
  automatically, 500 per run).