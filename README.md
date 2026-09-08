# Hockey Intelligence

An open-source NHL hockey intelligence platform: a FastAPI backend with a SQLite
database as the source of truth, a deterministic statistics engine, and a modular
Ollama-powered AI reasoning layer that explains database-verified facts — it never
invents numbers.

## Features

- **Player, team, and franchise data** from the NHL public APIs (regular season and
  playoffs), stored locally in SQLite.
- **Deterministic statistics engine** — career/season aggregation and multi-dimensional
  player comparison (offense, defense, puck skill, durability, efficiency). It never
  declares a single "winner".
- **Database-grounded AI assistant** — natural-language questions are answered by an
  Ollama model that selects tools; tool results are resolved against the database and
  fed back, so answers quote verified numbers.
- **Provider abstraction** — new data sources can be plugged in via `HockeyDataProvider`.
- **Historical awareness** — preserves defunct/relocated franchise identities (e.g.
  Hartford Whalers are not the Carolina Hurricanes).

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

# Seed the database (player/team data + 2024-25 stats + bios)
PYTHONPATH=. python scripts/seed.py 20242025

# Run the API
PYTHONPATH=. python -m uvicorn app.main:app --port 8000
# or: PYTHONPATH=. python scripts/run.py
```

Interactive docs: http://localhost:8000/docs

### Try it

```bash
# Search
curl "http://localhost:8000/api/search?q=McDavid"

# Profile + career stats
curl "http://localhost:8000/api/players/8478402"
curl "http://localhost:8000/api/players/8478402/career"

# Compare (evidence per dimension, no single winner)
curl -X POST "http://localhost:8000/api/compare/players?player_ids=8478402&player_ids=8478550"

# Database-grounded AI question
curl -X POST http://localhost:8000/api/ai/ask \
  -d '{"question": "How many points did Connor McDavid score in 2024-25, and how did his points-per-game compare to Artemi Panarin?"}'
```

## Architecture

```
app/
├── api/routes/        # HTTP layer (players, teams, statistics, ai)
├── core/config.py     # env-driven settings (pydantic-settings)
├── data/seeder.py     # ingestion pipeline from the NHL provider
├── database/          # async engine, sessions, init_db
├── models/            # SQLAlchemy models (24 tables)
├── providers/         # HockeyDataProvider ABC + NHL implementation
├── schemas/           # API response models
└── services/
    ├── ai/            # Ollama tool-calling loop + tool resolvers
    └── statistics/    # deterministic calculation engine
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
python -m pytest tests/ -q     # 22 tests
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
| `NHL_STATS_API_BASE` | `https://api.nhle.com/stats/rest/en` | NHL stats API |
| `NHL_WEB_API_BASE` | `https://api-web.nhle.com/v1` | NHL web API (bios) |

## Status & limitations

- Data is sourced from the NHL's public APIs; review their terms before redistribution.
- Schema evolves via `Base.metadata.create_all` (no Alembic migrations yet).
- Player bios are fetched for seeded players; more historical seasons can be added with
  `python scripts/seed.py 20152016 20242025`.