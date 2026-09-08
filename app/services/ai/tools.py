from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player
from app.models.stats import PlayerSeasonStats
from app.models.team import Team
from app.services.statistics.engine import StatisticsEngine

# ---------------------------------------------------------------------------
# Tool definitions (OpenAI tool-calling format, understood by Ollama)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_players",
            "description": (
                "Search for NHL players by name. Returns matching player IDs and "
                "basic info. Use this to resolve a player name before asking for "
                "their statistics."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Full or partial player name.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results, default 10.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_player",
            "description": (
                "Fetch basic biographical information for a player. Provide either "
                "a numeric player_id or the player's full_name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "player_id": {
                        "type": "integer",
                        "description": "NHL player ID (from search_players).",
                    },
                    "full_name": {
                        "type": "string",
                        "description": "Full player name, e.g. 'Connor McDavid'.",
                    },
                },
                "oneOf": [{"required": ["player_id"]}, {"required": ["full_name"]}],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_player_career_stats",
            "description": (
                "Fetch deterministic career statistics for a player: regular season "
                "and playoff totals for skaters and goalies. This data comes from "
                "the database and is the source of truth - never guess numbers. "
                "Provide either a numeric player_id or the player's full_name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "player_id": {
                        "type": "integer",
                        "description": "NHL player ID (from search_players).",
                    },
                    "full_name": {
                        "type": "string",
                        "description": "Full player name, e.g. 'Connor McDavid'.",
                    },
                },
                "oneOf": [{"required": ["player_id"]}, {"required": ["full_name"]}],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_player_season_stats",
            "description": (
                "Fetch a player's statistics for a specific season. season_id uses "
                "the form YYYYZZZZ e.g. 20242025 for the 2024-25 season. Provide "
                "either a numeric player_id or the player's full_name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "player_id": {"type": "integer"},
                    "full_name": {
                        "type": "string",
                        "description": "Full player name, e.g. 'Connor McDavid'.",
                    },
                    "season_id": {"type": "integer"},
                },
                "required": ["season_id"],
                "oneOf": [{"required": ["player_id"]}, {"required": ["full_name"]}],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_player_seasons_list",
            "description": (
                "List all seasons a player played in with basic season totals. "
                "Useful for 'which season was X's best' questions. Provide either "
                "a numeric player_id or the player's full_name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "player_id": {"type": "integer"},
                    "full_name": {
                        "type": "string",
                        "description": "Full player name, e.g. 'Connor McDavid'.",
                    },
                    "game_type": {
                        "type": "integer",
                        "description": "2 = regular season, 3 = playoffs. Default 2.",
                    },
                },
                "oneOf": [{"required": ["player_id"]}, {"required": ["full_name"]}],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_team",
            "description": (
                "Fetch a team (including historical team identities and franchise "
                "lineage) by team ID. Preserves historical franchises like the "
                "Hartford Whalers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "team_id": {"type": "integer"},
                },
                "required": ["team_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_teams",
            "description": (
                "Search for teams by name or city, including defunct and relocated "
                "franchises."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_players",
            "description": (
                "Compare two or more players across dimensions including offense, "
                "defense, puck skill, and durability. Returns evidence per dimension; "
                "it does not declare a single winner. Provide player_ids, or "
                "player_names (full names) which are resolved against the database."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "player_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                    },
                    "player_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "description": (
                            "Full names, e.g. ['Connor McDavid', 'Artemi Panarin']."
                        ),
                    },
                    "dimensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "offense, defense, puck_skill, durability, efficiency"
                        ),
                    },
                },
                "oneOf": [
                    {"required": ["player_ids"]},
                    {"required": ["player_names"]},
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_league_leaders",
            "description": (
                "Fetch league leaders for a statistic. Omit season_id for an "
                "all-time career leaderboard, or pass season_id (e.g. 20242025 for "
                "2024-25) for a single season. Skater stats: goals, assists, points, "
                "points_per_game, plus_minus, game_winning_goals, power_play_goals, "
                "shorthanded_goals, shots, shooting_pct, faceoff_win_pct, "
                "time_on_ice_per_game, hits, blocked_shots, takeaways, games_played. "
                "Goalie stats (stat_type='goalie'): wins, losses, shutouts, "
                "save_pct, goals_against_average, games_played. Rate stats are "
                "restricted to 30+ games by default in career scope; pass min_games "
                "to override."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "stat": {"type": "string", "description": "Statistic to rank."},
                    "season_id": {
                        "type": "integer",
                        "description": "Season ID like 20242025; omit for career.",
                    },
                    "stat_type": {
                        "type": "string",
                        "enum": ["skater", "goalie"],
                        "description": (
                            "Auto-detected from stat unless set explicitly."
                        ),
                    },
                    "game_type": {
                        "type": "integer",
                        "enum": [2, 3],
                        "description": "2 = regular season (default), 3 = playoffs.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results, default 10.",
                    },
                    "min_games": {
                        "type": "integer",
                        "description": (
                            "Minimum games played to qualify (rate stats only)."
                        ),
                    },
                },
                "required": ["stat"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_roster",
            "description": (
                "Fetch a team's roster for a season: the players who appeared for "
                "that team, with their games played."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "team_id": {"type": "integer"},
                    "season_id": {"type": "integer"},
                },
                "required": ["team_id", "season_id"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Tool handlers - each returns verified, database-grounded results
# ---------------------------------------------------------------------------


class ToolResults:
    """Registry that pairs tool schemas with their deterministic handlers."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.engine = StatisticsEngine(session)

    async def _execute(self, name: str, arguments: dict[str, Any]) -> Any:
        handler = getattr(self, f"_handle_{name}", None)
        if handler is None:
            return {"error": f"Unknown tool: {name}"}
        try:
            return await handler(arguments)
        except Exception as exc:  # pragma: no cover - defensive
            return {"error": str(exc)}

    async def _resolve_player(self, args: dict) -> tuple[int | None, dict]:
        """Resolve a player from either player_id or full_name against the DB."""
        if args.get("player_id") is not None:
            try:
                return int(args["player_id"]), {}
            except (TypeError, ValueError):
                return None, {"error": f"Invalid player_id {args['player_id']!r}."}
        name = (args.get("full_name") or "").strip()
        if not name:
            return None, {"error": "Provide either player_id or full_name."}
        result = await self.session.execute(
            select(Player).where(Player.full_name.ilike(f"%{name}%"))
        )
        matches = result.scalars().all()
        exact = [m for m in matches if (m.full_name or "").lower() == name.lower()]
        if len(exact) == 1:
            return exact[0].id, {}
        if len(exact) > 1:
            return None, {
                "error": f"Ambiguous player name '{name}'. Matches: "
                f"{[m.full_name for m in exact]}. Please disambiguate."
            }
        if len(matches) == 1:
            return matches[0].id, {}
        if len(matches) > 1:
            return None, {
                "error": f"Ambiguous player name '{name}'. Matches: "
                f"{[m.full_name for m in matches]}. Please disambiguate or provide a player_id."
            }
        return None, {
            "error": f"Player '{name}' not found in database. Do not invent statistics."
        }

    async def _handle_search_players(self, args: dict) -> dict:
        query = args.get("query", "")
        limit = min(args.get("limit") or 10, 50)
        term = f"%{query}%"
        result = await self.session.execute(
            select(Player)
            .where(
                Player.full_name.ilike(term)
                | Player.first_name.ilike(term)
                | Player.last_name.ilike(term)
            )
            .order_by(Player.full_name)
            .limit(limit)
        )
        players = result.scalars().all()
        return {
            "matches": [
                {
                    "player_id": p.id,
                    "full_name": p.full_name,
                    "position": p.position_code,
                    "active": bool(p.active),
                    "shoots_catches": p.shoots_catches,
                }
                for p in players
            ],
            "count": len(players),
            "disclaimer": (
                "If no match found, the player is not in the database. Do not "
                "invent their statistics."
            ),
        }

    async def _handle_get_player(self, args: dict) -> dict:
        pid, err = await self._resolve_player(args)
        if err:
            return err
        player = await self.session.get(Player, pid)
        if not player:
            return {"error": f"Player {pid} not found in database."}
        return {
            "player_id": player.id,
            "full_name": player.full_name,
            "position": player.position_code,
            "birth_date": player.birth_date.strftime("%Y-%m-%d")
            if player.birth_date is not None
            else None,
            "birth_city": player.birth_city,
            "birth_country": player.birth_country,
            "height": player.height,
            "weight": player.weight,
            "shoots_catches": player.shoots_catches,
            "draft_year": player.draft_year,
            "draft_round": player.draft_round,
            "draft_overall": player.draft_overall,
            "active": bool(player.active),
        }

    async def _handle_get_player_career_stats(self, args: dict) -> dict:
        pid, err = await self._resolve_player(args)
        if err:
            return err
        assert pid is not None
        return await self.engine.get_player_career_stats(pid)

    async def _handle_get_player_season_stats(self, args: dict) -> dict:
        pid, err = await self._resolve_player(args)
        if err:
            return err
        assert pid is not None
        season = int(args.get("season_id", 0))
        return await self.engine.get_player_season_stats(pid, season) or {
            "error": f"No statistics found for player {pid} in season {season}."
        }

    async def _handle_get_player_seasons_list(self, args: dict) -> dict:
        pid, err = await self._resolve_player(args)
        if err:
            return err
        game_type = int(args.get("game_type") or 2)
        stmt = (
            select(PlayerSeasonStats)
            .where(
                PlayerSeasonStats.player_id == pid,
                PlayerSeasonStats.game_type == game_type,
            )
            .order_by(PlayerSeasonStats.season_id)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        out = []
        for r in rows:
            out.append(
                {
                    "season_id": r.season_id,
                    "team": r.team_abbrevs,
                    "games_played": r.games_played,
                    "goals": r.goals,
                    "assists": r.assists,
                    "points": r.points,
                    "plus_minus": r.plus_minus,
                    "points_per_game": r.points_per_game,
                }
            )
        return {"player_id": pid, "seasons": out, "count": len(out)}

    async def _handle_get_team(self, args: dict) -> dict:
        tid = int(args.get("team_id", 0))
        team = await self.session.get(Team, tid)
        if not team:
            return {"error": f"Team {tid} not found in database."}
        identities = [
            {
                "name": i.name,
                "city": i.city,
                "abbr": i.abbr,
                "start_year": i.start_year,
                "end_year": i.end_year,
            }
            for i in team.identities
        ]
        franchise = None
        if team.franchise:
            franchise = {"id": team.franchise.id, "name": team.franchise.full_name}
        return {
            "team_id": team.id,
            "full_name": team.full_name,
            "abbreviation": team.abbreviation,
            "franchise": franchise,
            "active": bool(team.active),
            "first_season": team.first_season_id,
            "last_season": team.last_season_id,
            "identities": identities,
        }

    async def _handle_search_teams(self, args: dict) -> dict:
        query = args.get("query", "")
        limit = min(args.get("limit") or 15, 50)
        term = f"%{query}%"
        result = await self.session.execute(
            select(Team)
            .where(Team.full_name.ilike(term) | Team.city.ilike(term))
            .order_by(Team.full_name)
            .limit(limit)
        )
        teams = result.scalars().all()
        return {
            "matches": [
                {
                    "team_id": t.id,
                    "full_name": t.full_name,
                    "abbreviation": t.abbreviation,
                    "active": bool(t.active),
                }
                for t in teams
            ],
            "count": len(teams),
        }

    async def _handle_compare_players(self, args: dict) -> dict:
        player_ids: list[int] = []
        raw_ids = args.get("player_ids") or []
        if isinstance(raw_ids, str):
            raw_ids = []
        player_ids = [int(p) for p in raw_ids]
        for name in args.get("player_names") or []:
            resolved, err = await self._resolve_player({"full_name": name})
            if err:
                return err
            assert resolved is not None
            player_ids.append(resolved)
        dims = args.get("dimensions") or ["offense", "defense", "puck_skill", "durability"]
        if len(player_ids) < 2:
            return {
                "error": "compare_players requires at least 2 player IDs or names."
            }
        return await self.engine.compare_players(player_ids, dims)

    async def _handle_get_league_leaders(self, args: dict) -> dict:
        from app.services.statistics.engine import GOALIE_METRICS, SKATER_METRICS

        stat = (args.get("stat") or "points").lower()
        stat_type = (args.get("stat_type") or "").lower()
        if stat_type not in ("skater", "goalie"):
            stat_type = (
                "goalie"
                if stat in GOALIE_METRICS and stat not in SKATER_METRICS
                else "skater"
            )
        season_raw = args.get("season_id")
        season = int(season_raw) if season_raw not in (None, "") else None
        try:
            return await self.engine.get_leaderboard(
                season_id=season,
                metric=stat,
                stat_type=stat_type,
                game_type=int(args.get("game_type") or 2),
                limit=min(args.get("limit") or 10, 50),
                min_games=int(args["min_games"]) if args.get("min_games") else None,
            )
        except ValueError as exc:
            return {"error": str(exc)}

    async def _handle_get_team_roster(self, args: dict) -> dict:
        team_id = int(args.get("team_id", 0))
        season_id = int(args.get("season_id", 0))
        result = await self.session.execute(
            select(Player, PlayerSeasonStats)
            .join(PlayerSeasonStats, PlayerSeasonStats.player_id == Player.id)
            .where(
                PlayerSeasonStats.team_abbrevs.ilike(
                    self._team_abbr_filter(team_id)
                ),
                PlayerSeasonStats.season_id == season_id,
                PlayerSeasonStats.game_type == 2,
            )
            .order_by(Player.last_name)
        )
        rows = result.all()
        return {
            "team_id": team_id,
            "season_id": season_id,
            "roster": [
                {
                    "player_id": p.id,
                    "name": p.full_name,
                    "position": p.position_code,
                    "games_played": s.games_played,
                    "goals": s.goals,
                    "assists": s.assists,
                    "points": s.points,
                }
                for p, s in rows
            ],
            "count": len(rows),
        }

    async def _team_abbr_filter(self, team_id: int) -> str:
        team = await self.session.get(Team, team_id)
        if not team or not bool(team.abbreviation):
            return "%"
        return f"%{team.abbreviation}%"


def build_tool_schemas() -> list[dict[str, Any]]:
    return TOOL_DEFINITIONS


def tool_names() -> list[str]:
    return [t["function"]["name"] for t in TOOL_DEFINITIONS]
