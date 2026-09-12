from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player
from app.models.season import Season
from app.models.stats import GoalieSeasonStats, PlayerSeasonStats
from app.models.stats_team import TeamSeasonStats

SKATER_METRICS = {
    "games_played": "games_played",
    "goals": "goals",
    "assists": "assists",
    "points": "points",
    "points_per_game": "points_per_game",
    "plus_minus": "plus_minus",
    "penalty_minutes": "penalty_minutes",
    "power_play_goals": "pp_goals",
    "shorthanded_goals": "sh_goals",
    "game_winning_goals": "game_winning_goals",
    "shots": "shots",
    "shooting_pct": "shooting_pct",
    "faceoff_win_pct": "faceoff_win_pct",
    "time_on_ice_per_game": "time_on_ice_per_game",
    "hits": "hits",
    "blocked_shots": "blocked_shots",
    "takeaways": "takeaways",
}

GOALIE_METRICS = {
    "games_played": "games_played",
    "wins": "wins",
    "losses": "losses",
    "ot_losses": "ot_losses",
    "shutouts": "shutouts",
    "goals_against": "goals_against",
    "goals_against_average": "goals_against_average",
    "save_pct": "save_pct",
    "time_on_ice": "time_on_ice",
}

# Fantasy scoring presets. Entertainment only — never a claim about who is
# objectively best. Deterministic: computed from the same career aggregates the
# rest of the engine uses. Weights apply to career TOTALS; goalie save_pct bonus
# is applied to (save_pct - 0.900) so units stay comparable across shot volumes.
FANTASY_PRESETS: dict[str, dict] = {
    "standard": {
        "label": "Standard",
        "tagline": "Goals & helpers, with a slight bite for the penalty box.",
        "weights": {
            "goals": 3.0,
            "assists": 2.0,
            "plus_minus": 1.0,
            "penalty_minutes": -0.5,
            "shots": 0.25,
            "hits": 0.5,
            "blocked_shots": 0.5,
            "power_play_goals": 0.5,
            "shorthanded_goals": 1.0,
        },
        "goalie_weights": {"wins": 4.0, "shutouts": 5.0, "save_pct_bonus": 1200.0},
    },
    "bangers": {
        "label": "Bangers",
        "tagline": "Hit, block, shoot — the physical playbook.",
        "weights": {
            "goals": 2.5,
            "assists": 1.5,
            "plus_minus": 0.5,
            "penalty_minutes": 0.75,
            "shots": 0.5,
            "hits": 0.75,
            "blocked_shots": 1.0,
            "power_play_goals": 0.5,
            "shorthanded_goals": 1.0,
        },
        "goalie_weights": {"wins": 4.0, "shutouts": 4.0, "save_pct_bonus": 800.0},
    },
    "pure_points": {
        "label": "Pure points",
        "tagline": "Just the scoresheet basics.",
        "weights": {"goals": 1.0, "assists": 1.0},
        "goalie_weights": {"wins": 3.0, "shutouts": 2.0, "save_pct_bonus": 0.0},
    },
}

# rate metrics: (numerator column, denominator column, scale) — computed
# instead of summed directly in career scope; denominator units differ
_RATE_METRICS = {
    ("skater", "points_per_game"): ("points", "games_played", 1),
    ("goalie", "save_pct"): ("saves", "shots_against", 1),
    # time_on_ice is stored in seconds; GAA is per 60 minutes
    ("goalie", "goals_against_average"): ("goals_against", "time_on_ice", 3600),
}

_MIN_GAMES_IF_RATE = 30

DIMENSIONS = {
    "offense": {
        "label": "Offense",
        "metrics": [
            "era_adjusted_points",
            "points_per_game",
            "era_adjusted_ppg",
            "goals",
            "assists",
            "points",
        ],
    },
    "two_way": {
        "label": "Two-way",
        "metrics": [
            "plus_minus",
            "plus_minus_per_game",
            "takeaways",
            "hits",
            "blocked_shots",
            "sh_points",
        ],
    },
    "defense": {
        "label": "Two-way",
        "metrics": [
            "plus_minus",
            "plus_minus_per_game",
            "takeaways",
            "hits",
            "blocked_shots",
            "sh_points",
        ],
    },
    "puck_skill": {
        "label": "Puck Skill",
        "metrics": ["shooting_pct", "faceoff_win_pct"],
    },
    "efficiency": {
        "label": "Efficiency",
        "metrics": ["points_per_game", "shooting_pct"],
    },
    "durability": {
        "label": "Durability",
        "metrics": ["games_played", "seasons_played"],
    },
}

COMPARE_DEFAULT_DIMENSIONS = ["offense", "two_way", "puck_skill", "durability"]

# faceoff_win_pct was seeded with a placeholder of exactly 0.5 for seasons the
# provider did not report; treat that sentinel as "not tracked".
_FACEOFF_SENTINEL = 0.5


class StatisticsEngine:
    """Deterministic calculation layer.

    All calculated statistics live here. The AI layer consumes these
    results and explains them; it never computes them itself.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_player_career_stats(self, player_id: int) -> dict:
        skater = await self._aggregate_skater(
            PlayerSeasonStats, player_id, game_type=2
        )
        playoff_skater = await self._aggregate_skater(
            PlayerSeasonStats, player_id, game_type=3
        )
        goalie = await self._aggregate_goalie(
            GoalieSeasonStats, player_id, game_type=2
        )
        playoff_goalie = await self._aggregate_goalie(
            GoalieSeasonStats, player_id, game_type=3
        )
        return {
            "player_id": player_id,
            "regular_season": skater,
            "regular_season_goalie": goalie,
            "playoffs": playoff_skater,
            "playoffs_goalie": playoff_goalie,
        }

    async def get_player_season_stats(
        self, player_id: int, season_id: int
    ) -> dict | None:
        result = await self.session.execute(
            select(PlayerSeasonStats)
            .where(
                PlayerSeasonStats.player_id == player_id,
                PlayerSeasonStats.season_id == season_id,
                PlayerSeasonStats.game_type == 2,
            )
            .limit(1)
        )
        skater = result.scalar_one_or_none()

        goalie_result = await self.session.execute(
            select(GoalieSeasonStats)
            .where(
                GoalieSeasonStats.player_id == player_id,
                GoalieSeasonStats.season_id == season_id,
                GoalieSeasonStats.game_type == 2,
            )
            .limit(1)
        )
        goalie = goalie_result.scalar_one_or_none()

        if not skater and not goalie:
            return None
        return {
            "player_id": player_id,
            "season_id": season_id,
            "skater": self._row_to_dict(skater) if skater else None,
            "goalie": (
                {
                    "games_played": goalie.games_played,
                    "wins": goalie.wins,
                    "losses": goalie.losses,
                    "shutouts": goalie.shutouts,
                    "save_pct": goalie.save_pct,
                    "goals_against_average": goalie.goals_against_average,
                }
                if goalie
                else None
            ),
        }

    async def get_player_goalie_stats(self, player_id: int) -> dict | None:
        result = await self.session.execute(
            select(GoalieSeasonStats)
            .where(GoalieSeasonStats.player_id == player_id)
            .order_by(GoalieSeasonStats.season_id)
        )
        rows = result.scalars().all()
        return {
            "career": {
                "games_played": sum(r.games_played or 0 for r in rows),
                "wins": sum(r.wins or 0 for r in rows),
                "shutouts": sum(r.shutouts or 0 for r in rows),
                "save_pct": self._weighted_avg(
                    [r.save_pct for r in rows if r.save_pct is not None],
                    [r.shots_against or 0 for r in rows if r.save_pct is not None],
                ),
                "gaa": self._weighted_avg(
                    [r.goals_against_average for r in rows if r.goals_against_average is not None],
                    [r.time_on_ice or 0 for r in rows if r.goals_against_average is not None],
                ),
            }
        }

    async def _aggregate_skater(
        self, model, player_id: int, game_type: int = 2
    ) -> dict:
        stmt = select(model).where(
            model.player_id == player_id,
            model.game_type == game_type,
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        if not rows:
            return {}

        seasons = sum(1 for r in rows if (r.games_played or 0) > 0)
        games = sum(r.games_played or 0 for r in rows)
        goals = sum(r.goals or 0 for r in rows)
        assists = sum(r.assists or 0 for r in rows)
        points = goals + assists
        points_per_game = round(points / games, 3) if games else None

        return {
            "games_played": games,
            "goals": goals,
            "assists": assists,
            "points": points,
            "points_per_game": points_per_game,
            "plus_minus": sum(r.plus_minus or 0 for r in rows),
            "penalty_minutes": sum(r.penalty_minutes or 0 for r in rows),
            "game_winning_goals": sum(r.game_winning_goals or 0 for r in rows),
            "ot_goals": sum(r.ot_goals or 0 for r in rows),
            "power_play_goals": sum(r.pp_goals or 0 for r in rows),
            "shorthanded_goals": sum(r.sh_goals or 0 for r in rows),
            "shots": sum(r.shots or 0 for r in rows),
            "seasons_played": seasons,
        }

    async def _aggregate_goalie(
        self, model, player_id: int, game_type: int = 2
    ) -> dict:
        stmt = select(model).where(
            model.player_id == player_id,
            model.game_type == game_type,
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        if not rows:
            return {}

        saves = sum(r.saves or 0 for r in rows)
        shots_against = sum(r.shots_against or 0 for r in rows)
        return {
            "games_played": sum(r.games_played or 0 for r in rows),
            "games_started": sum(r.games_started or 0 for r in rows),
            "wins": sum(r.wins or 0 for r in rows),
            "losses": sum(r.losses or 0 for r in rows),
            "ot_losses": sum(r.ot_losses or 0 for r in rows),
            "shutouts": sum(r.shutouts or 0 for r in rows),
            "goals_against": sum(r.goals_against or 0 for r in rows),
            "shots_against": shots_against,
            "saves": saves,
            "save_pct": round(saves / shots_against, 4) if shots_against else None,
            "goals_against_average": (
                round(
                    sum(r.goals_against_average or 0 for r in rows) / len(rows), 3
                )
                if rows
                else None
            ),
            "seasons_played": len(rows),
        }

    @staticmethod
    def _row_to_dict(row) -> dict:
        return {
            "games_played": row.games_played,
            "goals": row.goals,
            "assists": row.assists,
            "points": row.points,
            "points_per_game": row.points_per_game,
            "plus_minus": row.plus_minus,
            "penalty_minutes": row.penalty_minutes,
            "power_play_goals": row.pp_goals,
            "shorthanded_goals": row.sh_goals,
            "game_winning_goals": row.game_winning_goals,
            "shots": row.shots,
            "shooting_pct": row.shooting_pct,
            "faceoff_win_pct": row.faceoff_win_pct,
            "time_on_ice_per_game": row.time_on_ice_per_game,
            "hits": row.hits,
            "blocked_shots": row.blocked_shots,
            "takeaways": row.takeaways,
        }

    @staticmethod
    def _weighted_avg(values: list, weights: list):
        if not values:
            return None
        total_w = sum(weights)
        if total_w == 0:
            return round(sum(values) / len(values), 4)
        return round(sum(v * w for v, w in zip(values, weights)) / total_w, 4)

    async def compare_players(
        self, player_ids: list[int], dimensions: list[str] | None = None
    ) -> dict:
        """Multi-dimensional player comparison.

        Returns evidence per dimension rather than a single ranking. Scoring is
        re-based to a common era so raw totals from different scoring eras are
        not compared unfairly, and the two-way dimension reports possession and
        physicality counters where the NHL tracked them (2007-08 onward).
        """
        dims = dimensions or COMPARE_DEFAULT_DIMENSIONS
        league_ppg = await self._league_ppg_by_season()
        profiles: dict[int, dict] = {}
        for pid in player_ids:
            profiles[pid] = await self._player_compare_profile(pid, league_ppg)

        comparison: dict = {
            "dimensions": dims,
            "players": [],
            "notes": [],
            "era": self._era_note(league_ppg),
        }

        for pid in player_ids:
            profile = await self.session.get(Player, pid)
            rs = profiles[pid]
            rs["name"] = profile.full_name if profile else str(pid)
            comparison["players"].append(
                {
                    "player_id": pid,
                    "name": rs["name"],
                    "position": profile.position_code if profile else None,
                    "games_played": round(rs["games_played"], 1),
                    "goals": round(rs["goals"], 1),
                    "assists": round(rs["assists"], 1),
                    "points": round(rs["points"], 1),
                    "points_per_game": rs["points_per_game"],
                    "era_adjusted_points": rs["era_adjusted_points"],
                    "era_adjusted_ppg": rs["era_adjusted_ppg"],
                    "pace_points_82": rs["pace_points_82"],
                    "plus_minus": rs["plus_minus"],
                    "plus_minus_per_game": rs["plus_minus_per_game"],
                    "penalty_minutes_per_game": rs["penalty_minutes_per_game"],
                    "seasons_played": rs["seasons_played"],
                    "power_play_goals": round(rs["pp_goals"], 1),
                    "shorthanded_goals": round(rs["sh_goals"], 1),
                    "shorthanded_points": round(rs["sh_points"], 1),
                    "game_winning_goals": round(rs["game_winning_goals"], 1),
                    "shooting_pct": rs["shooting_pct"],
                    "takeaways": rs["takeaways"],
                    "hits": rs["hits"],
                    "blocked_shots": rs["blocked_shots"],
                    "tracked_seasons": rs["tracked_seasons"],
                }
            )

        evidence = {}
        for dim in dims:
            evidence[dim] = self._dimension_evidence(player_ids, profiles, dim)

        comparison["evidence"] = evidence
        comparison["notes"] = self._comparison_notes(player_ids, profiles)
        comparison["data_notes"] = self._data_notes(player_ids, profiles)
        return comparison

    async def _league_ppg_by_season(self) -> dict[int, float]:
        """League-wide points-per-game for every tracked season.

        Used to re-base a player's scoring to a common era: each season's
        points are scaled by benchmark / season_league_ppg so a 1970s goal is
        not treated the same as a 2020s goal when comparing careers.
        """
        result = await self.session.execute(
            select(
                PlayerSeasonStats.season_id,
                func.sum(PlayerSeasonStats.points),
                func.sum(PlayerSeasonStats.goals),
                func.sum(PlayerSeasonStats.assists),
                func.sum(PlayerSeasonStats.games_played),
            )
            .where(
                PlayerSeasonStats.game_type == 2,
                PlayerSeasonStats.games_played > 0,
            )
            .group_by(PlayerSeasonStats.season_id)
        )
        out: dict[int, float] = {}
        for season_id, pts, goals, assists, gp in result.all():
            points = pts if pts is not None else (goals or 0) + (assists or 0)
            if gp:
                out[season_id] = points / gp
        return out

    async def _player_compare_profile(
        self, player_id: int, league_ppg: dict[int, float]
    ) -> dict:
        result = await self.session.execute(
            select(PlayerSeasonStats)
            .where(
                PlayerSeasonStats.player_id == player_id,
                PlayerSeasonStats.game_type == 2,
            )
            .order_by(PlayerSeasonStats.season_id)
        )
        rows = result.scalars().all()
        played = [r for r in rows if (r.games_played or 0) > 0]
        games = round(sum(r.games_played or 0 for r in played), 3)
        goals = sum(r.goals or 0 for r in played)
        assists = sum(r.assists or 0 for r in played)
        points = goals + assists
        seasons = len(played)

        benchmark = (league_ppg.get(max(league_ppg) or 0) or 1.0) if league_ppg else 1.0
        era_points = 0.0
        era_gp = 0.0
        for r in played:
            league = league_ppg.get(r.season_id) if r.season_id is not None else None
            factor = (benchmark / league) if league else 1.0
            season_points = (r.points if r.points is not None
                             else (r.goals or 0) + (r.assists or 0))
            era_points += season_points * factor
            era_gp += r.games_played or 0

        tracked = [r for r in played if (r.takeaways or 0) > 0]
        plus_minus = sum(r.plus_minus or 0 for r in played)
        sh_points = sum(r.sh_points or 0 for r in played)
        pp_goals = sum(r.pp_goals or 0 for r in played)
        sh_goals = sum(r.sh_goals or 0 for r in played)
        gwg = sum(r.game_winning_goals or 0 for r in played)
        pim = sum(r.penalty_minutes or 0 for r in played)

        shots = sum(r.shots or 0 for r in played)
        shooting_seen = [
            (r.shooting_pct or 0) for r in played if r.shooting_pct
        ]
        if shots > 0:
            shooting_pct = round(goals / shots, 4)
        elif shooting_seen:
            shooting_pct = round(sum(shooting_seen) / len(shooting_seen), 4)
        else:
            shooting_pct = None

        faceoff = self._avg_avail(
            [
                r.faceoff_win_pct
                for r in played
                if r.faceoff_win_pct is not None
                and r.faceoff_win_pct != _FACEOFF_SENTINEL
            ],
            None,
        )
        faceoff = round(faceoff, 4) if faceoff is not None else None

        takeaways = self._sum_avail([r.takeaways for r in played])
        hits = self._sum_avail([r.hits for r in played])
        blocked = self._sum_avail([r.blocked_shots for r in played])

        ppg = round(points / games, 4) if games else None
        era_ppg = round(era_points / era_gp, 4) if era_gp else None
        return {
            "games_played": games,
            "goals": goals,
            "assists": assists,
            "points": points,
            "points_per_game": ppg,
            "era_adjusted_points": round(era_points, 1),
            "era_adjusted_ppg": era_ppg,
            "pace_points_82": round((points / games) * 82, 1) if games else None,
            "plus_minus": plus_minus,
            "plus_minus_per_game": round(plus_minus / games, 4) if games else None,
            "penalty_minutes_per_game": round(pim / games, 4) if games else None,
            "seasons_played": seasons,
            "pp_goals": pp_goals,
            "sh_goals": sh_goals,
            "sh_points": sh_points,
            "game_winning_goals": gwg,
            "shooting_pct": shooting_pct,
            "faceoff_win_pct": faceoff,
            "takeaways": takeaways if tracked else None,
            "hits": hits if tracked else None,
            "blocked_shots": blocked if tracked else None,
            "tracked_seasons": len(tracked),
            "penalty_minutes": pim,
        }

    @staticmethod
    def _era_note(league_ppg: dict[int, float]) -> dict:
        bench = max(league_ppg) if league_ppg else None
        return {
            "benchmark_season": bench,
            "note": (
                f"Scoring re-based to {bench} league pace when the scoring era "
                "differs between players."
                if bench
                else "League scoring baseline unavailable."
            ),
        }

    def _data_notes(self, player_ids: list[int], profiles: dict[int, dict]) -> list[str]:
        notes = []
        for pid in player_ids:
            tracked = profiles[pid]["tracked_seasons"] or 0
            seasons = profiles[pid]["seasons_played"] or 0
            if seasons > 0 and tracked < seasons:
                notes.append(
                    f"{profiles[pid]['name'] or pid} has takeaways/hits/blocked shots "
                    f"tracked for {tracked} of their {seasons} "
                    "seasons — the NHL only tracked those counters from 2007-08, so "
                    "their earlier seasons read as blanks, not zeros."
                )
        return notes

    @staticmethod
    def _sum_avail(values: list) -> float | None:
        seen = [v for v in values if v is not None]
        return round(sum(seen), 1) if seen else None

    @staticmethod
    def _avg_avail(values: list, default=None) -> float | None:
        seen = [v for v in values if v is not None]
        return round(sum(seen) / len(seen), 4) if seen else default

    def _dimension_evidence(self, player_ids, profiles: dict[int, dict], dimension: str) -> dict:
        base_metrics = {
            "offense": ["era_adjusted_points", "points_per_game", "era_adjusted_ppg", "goals", "assists", "points"],
            "two_way": ["plus_minus", "plus_minus_per_game", "takeaways", "hits", "blocked_shots", "sh_points"],
            "defense": ["plus_minus", "plus_minus_per_game", "takeaways", "hits", "blocked_shots", "sh_points"],
            "puck_skill": ["shooting_pct", "faceoff_win_pct"],
            "efficiency": ["points_per_game", "shooting_pct"],
            "durability": ["games_played", "seasons_played"],
        }
        metrics = base_metrics.get(dimension, ["points"])
        leaders = {}
        for m in metrics:
            values = {}
            for pid in player_ids:
                v = profiles[pid].get(m)
                values[pid] = round(v, 4) if isinstance(v, float) else v
            leaders[m] = values
        return {
            "metric": metrics,
            "values": leaders,
            "interpretation": self._dimension_interpretation(dimension),
        }

    def _comparison_notes(self, player_ids, profiles: dict[int, dict]) -> list[str]:
        notes = []
        if len(player_ids) < 2:
            return notes
        stats = [(profiles[pid].get("points") or 0) for pid in player_ids]
        if len(set(stats)) == 1:
            notes.append(
                "The available data does not establish a meaningful difference in "
                "total scoring between these players."
            )
        return notes

    @staticmethod
    def _dimension_interpretation(dimension: str) -> str:
        return {
            "offense": (
                "Scoring. Era-adjusted points re-base each season's production to "
                "modern league scoring pace, so a 2002 season is compared fairly "
                "against a 2025 season instead of raw totals."
            ),
            "two_way": (
                "The all-situation game. Plus/minus while on ice, takeaways, hits, "
                "blocked shots and short-handed output. Takeaway/hit/blocked "
                "counters exist from 2007-08 — blanks predate tracking."
            ),
            "defense": (
                "The all-situation game. Plus/minus while on ice, takeaways, hits, "
                "blocked shots and short-handed output. Takeaway/hit/blocked "
                "counters exist from 2007-08 — blanks predate tracking."
            ),
            "puck_skill": (
                "Rate quality: shooting accuracy and (where tracked) faceoff win "
                "rate — freed from season length."
            ),
            "durability": "Games played and seasons sustained at the NHL level.",
            "efficiency": (
                "Production relative to opportunity: points per game and shooting "
                "percentage."
            ),
        }.get(
            dimension,
            "Dimension requires additional context. Available statistics are limited.",
        )

    async def get_team_career_history(self, team_id: int) -> dict:
        result = await self.session.execute(
            select(TeamSeasonStats)
            .where(TeamSeasonStats.team_id == team_id)
            .order_by(TeamSeasonStats.season_id)
        )
        rows = result.scalars().all()
        return {
            "team_id": team_id,
            "seasons": [
                {
                    "season_id": r.season_id,
                    "games_played": r.games_played,
                    "wins": r.wins,
                    "losses": r.losses,
                    "ot_losses": r.ot_losses,
                    "points": r.points,
                    "goals_for": r.goals_for,
                    "goals_against": r.goals_against,
                }
                for r in rows
            ],
        }

    async def get_leaderboard(
        self,
        *,
        season_id: int | None = None,
        metric: str = "points",
        game_type: int = 2,
        stat_type: str = "skater",
        limit: int = 10,
        min_games: int | None = None,
    ) -> dict:
        """Season or all-time leaderboard for a single metric.

        `season_id=None` returns career totals (grouped across seasons). Rate
        metrics (points_per_game, save_pct, goals_against_average) default to a
        30-game minimum in career scope unless `min_games` is given explicitly.
        """
        stat_type = stat_type.lower()
        metrics = SKATER_METRICS if stat_type == "skater" else GOALIE_METRICS
        if metric not in metrics:
            raise ValueError(
                f"Unknown {stat_type} metric '{metric}'. "
                f"Available: {', '.join(sorted(metrics))}"
            )
        column = metrics[metric]

        model = PlayerSeasonStats if stat_type == "skater" else GoalieSeasonStats

        if season_id is not None:
            results = await self._season_leaderboard(
                model, season_id, game_type, column, limit, min_games
            )
        else:
            results = await self._career_leaderboard(
                model, game_type, stat_type, metric, column, limit, min_games
            )

        scope = "season" if season_id is not None else "career"
        payload: dict = {
            "scope": scope,
            "season_id": season_id,
            "game_type": game_type,
            "stat_type": stat_type,
            "metric": metric,
            "limit": limit,
            "min_games": min_games,
            "results": results,
        }
        if season_id is not None:
            season = await self.session.get(Season, season_id)
            payload["season_label"] = season.formatted_id if season else str(season_id)
        return payload

    async def get_fantasy_pool(
        self,
        *,
        preset: str = "standard",
        stat_type: str = "skater",
        limit: int = 160,
        game_type: int = 2,
    ) -> dict:
        """Career fantasy pool for one scoring preset.

        Entertainment, for fun — never a claim about who is objectively best.
        Fantasy points are computed deterministically from the same career
        aggregates the leaderboards use.
        """
        stat_type = stat_type.lower()
        if preset not in FANTASY_PRESETS:
            raise ValueError(
                f"Unknown fantasy preset '{preset}'. "
                f"Available: {', '.join(sorted(FANTASY_PRESETS))}"
            )
        meta = FANTASY_PRESETS[preset]

        model = PlayerSeasonStats if stat_type == "skater" else GoalieSeasonStats
        weights = meta["weights"] if stat_type == "skater" else meta["goalie_weights"]

        if stat_type == "skater":
            weight_cols = [
                (k, SKATER_METRICS[k], w)
                for k, w in weights.items()
                if k in SKATER_METRICS
            ]
            agg_cols = ["games_played"] + [c for _, c, _ in weight_cols]
        else:
            weight_cols = [
                ("wins", "wins", weights.get("wins", 0.0)),
                ("shutouts", "shutouts", weights.get("shutouts", 0.0)),
            ]
            agg_cols = ["games_played", "wins", "shutouts", "saves", "shots_against"]

        sums = await self._career_sums(model, game_type, agg_cols)
        recent_team = await self._recent_team_by_player(model, game_type)

        player_ids = list(sums)
        player_map = await self._player_cards(player_ids)

        pickable = []
        for pid, bucket in sums.items():
            if stat_type == "skater":
                fp = sum(bucket[c] * w for _, c, w in weight_cols)
            else:
                fp = sum(bucket[c] * w for _, c, w in weight_cols)
                made = bucket.get("saves") or 0
                faced = bucket.get("shots_against") or 0
                if faced:
                    fp += ((made / faced) - 0.900) * weights.get("save_pct_bonus", 0.0)
            gp = bucket.get("games_played") or 0
            metrics = {
                k: (round(bucket[c], 4) if isinstance(bucket[c], float) else bucket[c])
                for k, c, _ in weight_cols
            }
            if stat_type == "goalie":
                made = bucket.get("saves") or 0
                faced = bucket.get("shots_against") or 0
                if faced:
                    metrics["save_pct"] = round(made / faced, 4)
            player = player_map.get(pid)
            pickable.append(
                {
                    "player_id": pid,
                    "name": player["full_name"] if player else str(pid),
                    "team": recent_team.get(pid),
                    "position": player["position_code"] if player else None,
                    "games_played": int(gp),
                    "fp": round(fp, 1),
                    "fp_per_game": round(fp / gp, 2) if gp else None,
                    "metrics": metrics,
                }
            )

        pickable.sort(key=lambda p: p["fp"], reverse=True)
        for rank, row in enumerate(pickable[:limit], start=1):
            row["rank"] = rank

        return {
            "role": stat_type,
            "preset": preset,
            "preset_label": meta["label"],
            "preset_tagline": meta["tagline"],
            "results": pickable[:limit],
        }

    async def _player_cards(self, player_ids: list[int]) -> dict[int, dict]:
        """id -> {full_name, position_code} without full ORM hydration."""
        if not player_ids:
            return {}
        rows = (
            await self.session.execute(
                select(Player.id, Player.full_name, Player.position_code).where(
                    Player.id.in_(player_ids)
                )
            )
        ).all()
        return {i: {"full_name": n, "position_code": p} for i, n, p in rows}

    async def _career_sums(self, model, game_type: int, columns: list[str]):
        """Per-player career totals via a single SQL GROUP BY (no row hydration)."""
        exprs = [
            func.coalesce(func.sum(getattr(model, c)), 0).label(c) for c in columns
        ]
        stmt = (
            select(model.player_id, *exprs)
            .where(model.game_type == game_type, model.player_id.is_not(None))
            .group_by(model.player_id)
        )
        rows = (await self.session.execute(stmt)).all()
        return {r[0]: {c: r[i + 1] for i, c in enumerate(columns)} for r in rows}

    async def _recent_team_by_player(self, model, game_type: int) -> dict[int, str]:
        """Most recent season's team abbreviation per player (windowed, one row each)."""
        rn = func.row_number().over(
            partition_by=model.player_id, order_by=model.season_id.desc()
        ).label("rn")
        sub = (
            select(model.player_id.label("player_id"), model.team_abbrevs, rn)
            .where(model.game_type == game_type)
            .subquery()
        )
        rows = (
            await self.session.execute(
                select(sub.c.player_id, sub.c.team_abbrevs).where(sub.c.rn == 1)
            )
        ).all()
        return {
            pid: ab for pid, ab in rows if pid is not None and ab
        }

    async def _season_leaderboard(
        self, model, season_id, game_type, column, limit, min_games
    ) -> list[dict]:
        stmt = (
            select(model, Player)
            .join(Player, model.player_id == Player.id)
            .where(model.season_id == season_id, model.game_type == game_type)
        )
        rows = (await self.session.execute(stmt)).all()

        qualified = []
        for row, player in rows:
            value = getattr(row, column)
            if value is None:
                continue
            if min_games is not None and (row.games_played or 0) < min_games:
                continue
            qualified.append((value, player, row))
        qualified.sort(key=lambda t: t[0], reverse=True)

        ranked = []
        for idx, (value, player, row) in enumerate(qualified):
            rank = idx + 1
            if idx > 0 and value == qualified[idx - 1][0]:
                rank = ranked[idx - 1]["rank"]
            ranked.append(
                {
                    "rank": rank,
                    "player_id": player.id,
                    "name": player.full_name,
                    "team": row.team_abbrevs,
                    "position": player.position_code,
                    "value": round(value, 4) if isinstance(value, float) else value,
                }
            )
        return ranked[: self._leaderboard_cutoff(ranked, limit)]

    @staticmethod
    def _leaderboard_cutoff(ranked: list[dict], limit: int) -> int:
        """Rank positions are stable after limit, but keep players tied with it."""
        if len(ranked) <= limit:
            return len(ranked)
        cutoff_value = ranked[limit - 1]["value"]
        idx = limit
        while idx < len(ranked) and ranked[idx]["value"] == cutoff_value:
            idx += 1
        return idx

    async def _career_leaderboard(
        self, model, game_type, stat_type, metric, column, limit, min_games
    ) -> list[dict]:
        rate_sources = _RATE_METRICS.get((stat_type, metric))
        if min_games is None and rate_sources:
            min_games = _MIN_GAMES_IF_RATE

        agg_cols = ["games_played"]
        if rate_sources:
            num, den, _ = rate_sources
            agg_cols += [num, den]
        else:
            agg_cols.append(column)

        sums = await self._career_sums(model, game_type, agg_cols)
        recent_team = await self._recent_team_by_player(model, game_type)

        qualified = []
        for player_id, vals in sums.items():
            games = vals["games_played"] or 0
            if min_games is not None and games < min_games:
                continue
            if rate_sources:
                num, den, scale = rate_sources
                value = vals[num] * scale / vals[den] if vals[den] else None
            else:
                value = vals[column]
            if value is None:
                continue
            qualified.append((player_id, value))

        player_ids = [pid for pid, _ in qualified]
        player_map = await self._player_cards(player_ids)

        qualified.sort(key=lambda t: t[1], reverse=True)

        ranked = []
        for idx, (player_id, value) in enumerate(qualified, start=1):
            player = player_map.get(player_id)
            ranked.append(
                {
                    "rank": idx,
                    "player_id": player_id,
                    "name": player["full_name"] if player else str(player_id),
                    "team": recent_team.get(player_id),
                    "position": player["position_code"] if player else None,
                    "value": round(value, 4) if isinstance(value, float) else value,
                }
            )
        return ranked[: self._leaderboard_cutoff(ranked, limit)]
