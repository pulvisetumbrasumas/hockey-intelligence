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
- `app/services/statistics/engine.py` — deterministic aggregation + compare engine +
  leaderboards (season or career; skater/goalie metrics; tie handling; min-games guard
  for rate stats: points_per_game, save_pct, GAA).
- `app/services/ai/service.py` — Ollama tool-calling loop, system prompt, health.
- `app/services/ai/tools.py` — 10 tool schemas + `ToolResults` handlers (incl.
  `get_league_leaders` backed by the leaderboard engine).
- `app/api/routes/{players,teams,platform,statistics,ai}.py` — assembled in
  `routes/__init__.py`. `platform.py` adds season-facts, events, schedule proxy and
  standings (computed from `team_season_stats`) plus a `seasons` archive list.
- `app/services/images.py` — deterministic NHL media URL builders (headshots, hero
  shots, team SVG logos via `assets.nhle.com`).
- `app/services/media.py` — resolves each player's most recent team abbreviation from
  `player_season_stats` (one grouped query) so the UI can build headshot/hero URLs.
- `app/static/` — premium cinematic application shell served at `/`:
  - `css/styles.css` — full design system (dark navy/black, ice-cyan + blue gradient
    accent, glass surfaces, thin glowing borders, LED countdown, scoreboard, tables,
    radar, timeline; responsive + `prefers-reduced-motion`; no external fonts).
  - `js/app.js` — hash router, nav (15 destinations), global search (/ key), local
    account + favorites (localStorage), notifications modal, toasts, countdown helper.
  - `js/pages/*.js` — home (hero + data-driven countdown to 2026-27 start from
    `/api/season-facts`, today's games, featured player = real career points leader,
    standings preview, events), players (+profile with career/season + PPG chart),
    teams (+club identity timeline), franchises (lineage), standings (+leaderboards),
    compare (canvas radar, no single winner), ai (chat with provenance), live, schedule,
    events (countdown timeline), history (seasons archive), fantasy (experimental
    watchlist from real leaderboards), news (shell), favorites, settings.
  - Static mount is registered LAST so /docs, /health and /api/* win.
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
- `/api/stats/leaders/season/20242025?metric=goals` → Draisaitl 52 (correct 2024-25 Rocket)
- `/api/stats/leaders/career?metric=points` → McDavid 1082 (2015-16 onward data)
- `POST /api/compare/players?player_ids=...&player_ids=...` → multi-dim evidence, no single winner
- `POST /api/ai/ask` with `{"question": "..."}` → grounded, correct answer (~150s with llama3.2)
- `/` serves the web UI (search, career + season bars, leaders, compare, AI chat)

Seeded data: 109 seasons, 62 team identities, 40 franchises, **2259 players (all with
bios)**, 10 seasons of skater/goalie stats (2015-16 → 2024-25, reg + playoffs),
12,449 skater rows + 1,267 goalie rows, 32 teams with season stats.

## Records / leaders engine notes

- `get_leaderboard(season_id=None|N, metric, stat_type, game_type, limit, min_games)`.
  Career scope groups across seasons; goals/assists/points etc. are summed, while
  points_per_game / save_pct / GAA are recomputed from raw totals (GAA scaled to 60
  min; `time_on_ice` is stored in seconds).
- Rate metrics default to a 30-game minimum in career scope (`_MIN_GAMES_IF_RATE`)
  to avoid a 2-game call-up topping the PPG list; pass `min_games` to override.
- Ties keep identical ranks (competition ranking) and extend past `limit`.
- Goalies live only in `goalie_season_stats`; skaters have `is_goalie=0` — leaderboards
  are therefore uncontaminated, no filter needed beyond choosing the table.

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

## Phase 1 — cinematic application shell (verified)

- Serves a full premium SPA at `/`: dark navy/black base, ice-cyan/blue gradient accent,
  glass panels, thin glowing borders, LED-style countdown boxen, marquee-free hero,
  responsive desktop-first + reduced-motion support, zero external dependencies
  (no webfonts). Verified endpoint-by-endpoint (all 200): `/`, `/css/styles.css`,
  each `/js/*.js`, `/api/season-facts`, `/api/events`, `/api/schedule?date=today`,
  `/api/standings`, `/api/seasons`, `/api/search`, `/api/franchises/{id}`, `/docs`.
- Countdown is data-driven: `/api/season-facts` merges the NHL schedule API dates
  (regular-season start/end, playoff window) with DB league size; `/api/events` lists
  those plus configured trade deadline/draft/all-star. The UI never hard-codes dates.
- Standings are computed from `team_season_stats` (points → reg wins → goal diff);
  verified 2024-25: WPG #1 (116), NJD #16. Playoff bubble = top 16 league-wide.
- Player/team/franchise pages pull real DB data; player headshots/hero shots and team
  SVG logos are built by `services/images.py` from the DB (abbr + nhl_id) and resolve
  against `assets.nhle.com` (verified 200).
- Schedule/live boards proxy the NHL schedule endpoint (short TTL cache).
- Account + favorites are local-first (localStorage); server accounts are a later slice.
- Compare shows per-dimension evidence + radar; no winner. Under the hood
  `puck_skill` currently lacks data (no shooting_pct in career aggregate), so that axis
  is omitted gracefully.
- Media URLs: headshots/heroes resolve from the most recent listed team per player
  (`services/media.py`, single grouped query). Players with no stats rows get no image
  and show a monogram instead.

## Remaining / known issues

- LSP noise (not runtime): `pydantic_settings` "could not be resolved" (stale index,
  package installed); stale Column-type errors in `players.py`/`teams.py` from before
  the `Mapped[]` conversion; str|None→str annotations on `full_name` in a few spots.
- Alembic migration strategy added (baseline + stamped DB); `init_db` in lifespan/seed
  remains as a `create_all` convenience and is a no-op on migrated DBs.
- Goalie rate leaderboards in a single season can surface tiny-sample backups
  (emergency call-ups with a few minutes). Season endpoints accept `min_games` to
  filter; the AI tool passes it when the user asks for starters/qualified goalies.
- Two placeholder team rows exist from the API ("To be determined"/TBD, "NHL"/NHL);
  filter them out of search if they surface.
- Establishment of NHL API redistribution/licensing terms still pending review.

## Typical next steps

1. Speed up the AI loop further: streaming/SSE, per-turn `num_ctx` tuning, or a faster model.
2. Deeper history: seed pre-2015 seasons so career leaderboards and the History archive go back further.
3. Team season endpoints + per-team charts; game-event/streaks engine; conference/division splits in standings.
4. Server-side accounts (users table + migration), favorites backend, notifications tied to events.
5. Return-of-playoff content: champions, playoffs brackets, series data per season.
6. Fantasy slice: draft room with scoring systems over real stats.