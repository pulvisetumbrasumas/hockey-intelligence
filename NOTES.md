# Hockey Intelligence — Project Notes

Open-source NHL hockey intelligence platform. FastAPI backend, SQLite/SQLAlchemy as
source of truth, a deterministic statistics engine, and a modular Ollama AI reasoning
layer that never invents numbers.

## Goal (the vertical slice)

Smallest deliverable first: search player → player profile → player statistics →
player comparison → one database-grounded AI question. Clean layer separation and a
provider abstraction so future data sources can be added.

## Stack / decisions

- Python 3.14.7, FastAPI 0.137.2, SQLAlchemy 2.0.51 (async, `aiosqlite`), Pydantic,
  uvicorn, httpx, pydantic-settings. Node/Rust available but unused.
- DB is source of truth → statistics engine is deterministic → Ollama only reasons/
  explains using verified tool results.
- Config-driven AI: `OLLAMA_MODEL` (default now `llama3.2:latest`), `OLLAMA_BASE_URL`,
  `OLLAMA_TEMPERATURE`, `OLLAMA_NUM_CTX`, `OLLAMA_TIMEOUT` (set to 420).
- Data sources:
  - NHL Stats API `https://api.nhle.com/stats/rest/en` (team, franchise, season,
    skater/summary, goalie/summary; `cayenneExp`, `start`, `limit`, `isAggregate=false`)
  - NHL Web API `https://api-web.nhle.com/v1` (player/{id}/landing for bios)

## Layout

- `app/main.py` — FastAPI entry; lifespan runs `init_db` + `ensure_data_source`.
- `app/core/config.py` — env-driven settings; `get_settings()` cached.
- `app/database/connection.py` — async engine, session factory, `get_db`, `init_db`.
- `app/models/*.py` — 24 tables, `Mapped[]` style; `__init__.py` re-exports.
- `app/providers/base.py` — `HockeyDataProvider` ABC.
- `app/providers/nhl_provider.py` — stats + web API clients.
- `app/data/seeder.py` — ingestion pipeline; records provenance in `data_imports`.
- `app/services/statistics/engine.py` — deterministic aggregation + compare engine.
- `app/services/ai/service.py` — Ollama tool-calling loop, system prompt, health.
- `app/services/ai/tools.py` — 10 tool schemas + `ToolResults` handlers.
- `app/api/routes/{players,teams,statistics,ai}.py` — assembled in `routes/__init__.py`.
- `scripts/seed.py` / `scripts/run.py` — helpers.

## How to run

```bash
cd /home/animainvicta/Projects/hockey-intelligence

# seed (needs PYTHONPATH because scripts run from repo root)
PYTHONPATH=. python scripts/seed.py 20242025

# run server
PYTHONPATH=. python -m uvicorn app.main:app --port 8000
# or: PYTHONPATH=. python scripts/run.py

# Ollama must be listening on http://localhost:11434
ollama serve
```

## Verified end-to-end (current DB)

- `/api/search?q=McDavid` → player found
- `/api/players/8478402` → bio profile
- `/api/players/8478402/career` → 67 GP / 26 G / 74 A / 100 Pts / 1.493 PPG (reg) + playoffs
- `POST /api/compare/players?player_ids=...&player_ids=...` → multi-dim evidence, no single winner
- `POST /api/ai/ask` with `{"question": "..."}` → grounded, correct answer (~150s with llama3.2)

Seeded data: 109 seasons, 62 team identities, 40 franchises, **2259 players (all with
bios)**, 10 seasons of skater/goalie stats (2015-16 → 2024-25, reg + playoffs),
12,449 skater rows + 1,267 goalie rows, 32 teams with season stats.

## Database migrations (Alembic)

- `migrations/` + `alembic.ini`; `migrations/env.py` is async, sets
  `target_metadata` from the models and reads `DATABASE_URL` from `.env`.
- Baseline `333a3d9a45d5` created against an empty DB; verified: `upgrade head`
  reproduces the full schema on a fresh DB and table sets match the existing dev DB.
- Existing dev DB is stamped at head (`alembic stamp head`).
- Generated migrations carry E501/W291 → relaxed via per-file-ignores in pyproject.

## Bugs fixed during development (important gotchas)

1. `GameEvent.player` relationship: ambiguous FKs because assist columns also point at
   players → must pass `foreign_keys=[player_id]`.
2. Seeder `_get_or_create` used to `flush()` immediately — a brand-new row was INSERTed
   with `None` values, tripping NOT NULL constraints. Now it just `add()`s and relies on
   autoflush after the caller sets fields.
3. NHL API `sort` param: `quote(...)` pre-encoded, then httpx encoded `%` again →
   double encoding (`%25`). Pass raw JSON and let httpx percent-encode.
4. Playoff stats were being stored as `game_type=2` because `_upsert_skater`/`_upsert_goalie`
   hardcoded it. Now takes a `game_type` param (default 2).
5. Running `pkill -f "uvicorn app.main:app"` matches the shell's own command line and
   kills it. Start the server detached with `setsid ... & disown`; kill via PID.

## AI layer notes (model behavior on this hardware)

- `qwen3:4b`: reasons well, calls `search_players` first, uses real IDs — but ~200s PER
  TOOL TURN (spends ~200s on internal reasoning, zero streamed tokens). A single question
  took 10+ minutes and still hit the 420s timeout. Impractical as default.
- `llama3.2:latest`: ~60s/turn, finished a full grounded question in ~150s. But it:
  - fabricated player IDs (e.g. `1234567890`) instead of searching,
  - passed arrays as JSON strings (`"[1, 2]"` instead of `[1, 2]`).
- Fixes applied:
  - `_coerce()` in `service.py` recursively parses JSON-string args into real values.
  - Tools now accept `full_name` as an alternative to numeric `player_id`
    (`get_player`, `get_player_career_stats`, `get_player_season_stats`,
    `get_player_seasons_list`) and `compare_players` accepts `player_names`.
    `ToolResults._resolve_player()` resolves names deterministically against the DB and
    refuses to invent data on ambiguous/no match.
  - System prompt rule 4: never guess/fabricate numeric IDs; pass full names or use
    `search_players`.
- Switch model any time via `OLLAMA_MODEL` in `.env` (e.g. back to `qwen3:4b`).

## Remaining / known issues

- LSP noise (not runtime): `pydantic_settings` "could not be resolved" (stale index,
  package installed); stale Column-type errors in `players.py`/`teams.py` from before
  the `Mapped[]` conversion.
- Alembic migration strategy added (baseline + stamped DB); `init_db` in lifespan/seed
  remains as a `create_all` convenience and is a no-op on migrated DBs.
- Two placeholder team rows exist from the API ("To be determined"/TBD, "NHL"/NHL);
  filter them out of search if they surface.
- Establishment of NHL API redistribution/licensing terms still pending review.

## Typical next steps

1. Speed up the AI loop further: streaming, per-turn `num_ctx` tuning, or a faster model.
2. Surface the decided "no single winner" comparison as the default UX; add an
   `OLLAMA_KEEP_ALIVE`-aware connection pool if embedding queries grow.
3. Expand to more historical seasons or split/season endpoints as needed.