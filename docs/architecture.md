# Architecture

## Overview

Hockey Intelligence is a layered application. The database is the source of
truth; every number that reaches a user was computed from database rows by the
deterministic statistics engine. The AI layer is an explainer: it calls tools,
gets verified results, and reasons over them. It is never allowed to compute or
invent statistics.

```
NHL public APIs (providers)
        │
        ▼
   Seeder ──► SQLite  ──► StatisticsEngine (deterministic)
                         │        │
                         ▼        ▼
                   REST API   AI tools ←── Ollama model
```

## Layers

### Providers (`app/providers/`)

`HockeyDataProvider` is the abstraction. `NHLDataProvider` implements it with two
clients:

- **Stats API** (`api.nhle.com/stats/rest/en`) — skater/goalie/team/season
  summaries, franchises. Pagination uses `start`/`limit`; the API's `sort`
  parameter must be passed as raw JSON (never pre-encoded — httpx will
  percent-encode it once).
- **Web API** (`api-web.nhle.com/v1`) — player landing pages for bios.

A new provider (e.g. a different stats feed) implements the same interface.

### Seeder (`app/data/seeder.py`)

Ingests franchises, team identities, seasons, and per-season skater/goalie/team
statistics (regular season `game_type=2` and playoffs `game_type=3`), plus
player bios. Idempotent: rows are `get_or_create`'d and refreshed, never
duplicated. New objects are `add()`ed and left for autoflush — an eager `flush()`
would INSERT rows with `None` values before attributes are set.

### Statistics engine (`app/services/statistics/engine.py`)

Pure aggregation over ORM rows:

- `get_player_career_stats` — regular + playoff totals for skaters and goalies.
  Points-per-game = `points/games` (rounded to 3), `None` when no games.
  `seasons_played` only counts rows with `games_played > 0`.
- `get_player_season_stats`, `get_player_seasons_list` — per-season views.
- `compare_players` — multi-dimensional comparison. For every dimension
  (offense, defense, puck_skill, durability, efficiency) it reports per-player
  metric values and an interpretation. It never returns a single "winner".

### AI layer (`app/services/ai/`)

- `tools.py` — tool schemas (OpenAI tool-calling format that Ollama understands)
  plus `ToolResults`, a registry of deterministic handlers backed by the
  statistics engine and database session. `_resolve_player` maps a `full_name`
  to a numeric ID in the database (rejecting ambiguous/unknown names), so the
  model never needs to know IDs.
- `service.py` — `OllamaAIService.ask()` runs the agent loop:

  1. Send system prompt + user question, with tool schemas.
  2. When the model returns `tool_calls`, execute them, append each result as a
     `role: "tool"` message, and repeat (bounded, 8 iterations).
  3. When the model answers without tool calls, return the answer plus
     `provenance` (which tools ran, with args and results).

  `_coerce()` recursively parses argument values that models sometimes emit as
  JSON strings (e.g. `"[1, 2]"` → `[1, 2]`).

## Database

24 tables across players/teams/franchises/seasons/stats/games/transactions/
contracts/drafts/awards/coaches/GMs. Foreign keys on ambiguous relationships
(e.g. `GameEvent` has player plus two assist FKs to the same table) require an
explicit `foreign_keys=` argument.

SQLite via `aiosqlite` + SQLAlchemy 2.0 `Mapped[]` models. Schema changes are managed
with Alembic: `migrations/env.py` wires the async engine and `target_metadata` from the
models, reading `DATABASE_URL` from `.env`. The baseline migration stamps the existing
dev DB at head; `alembic upgrade head` reproduces the full schema on a fresh DB.
`init_db` (`Base.metadata.create_all`) remains a convenience fallback in lifespan/seed
and is a no-op once a DB is migrated.

## Data provenance

`data_imports` records each ingestion batch (source, type, row count, timestamp,
URL), so the database can explain where its rows came from.

## Concurrency / performance notes

- The AI loop is slow on CPU-only hardware: llama3.2 ~60s per tool turn,
  qwen3:4b ~3x that. Adjust `OLLAMA_TIMEOUT` (default 420). Each chat request sends
  `keep_alive` (default `10m`) so the model stays loaded between questions.
- The model is kept configurable via `OLLAMA_MODEL`; the application code does
  not depend on any specific model.