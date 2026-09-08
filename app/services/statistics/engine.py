from sqlalchemy import select
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
        "metrics": ["goals", "assists", "points", "points_per_game"],
    },
    "defense": {
        "label": "Defense",
        "metrics": ["plus_minus", "blocked_shots", "takeaways", "hits"],
    },
    "puck_skill": {
        "label": "Puck Skill",
        "metrics": ["time_on_ice_per_game", "faceoff_win_pct", "shooting_pct"],
    },
    "efficiency": {
        "label": "Efficiency",
        "metrics": ["points_per_game", "shooting_pct", "faceoff_win_pct"],
    },
    "durability": {
        "label": "Durability",
        "metrics": ["games_played"],
    },
}


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

        Returns evidence per dimension rather than a single ranking.
        """
        dims = dimensions or ["offense", "defense", "puck_skill", "durability"]
        players_stat = {}
        for pid in player_ids:
            players_stat[pid] = await self.get_player_career_stats(pid)

        comparison = {
            "dimensions": dims,
            "players": [],
            "notes": [],
        }

        for pid in player_ids:
            profile = await self.session.get(Player, pid)
            rs = players_stat[pid].get("regular_season") or {}
            comparison["players"].append(
                {
                    "player_id": pid,
                    "name": profile.full_name if profile else str(pid),
                    "position": profile.position_code if profile else None,
                    "games_played": rs.get("games_played"),
                    "goals": rs.get("goals"),
                    "assists": rs.get("assists"),
                    "points": rs.get("points"),
                    "points_per_game": rs.get("points_per_game"),
                    "plus_minus": rs.get("plus_minus"),
                    "seasons_played": rs.get("seasons_played"),
                    "power_play_goals": rs.get("power_play_goals"),
                    "shorthanded_goals": rs.get("shorthanded_goals"),
                    "game_winning_goals": rs.get("game_winning_goals"),
                }
            )

        # Per-dimension evidence
        evidence = {}
        for dim in dims:
            evidence[dim] = self._dimension_evidence(player_ids, players_stat, dim)

        comparison["evidence"] = evidence
        comparison["notes"] = self._comparison_notes(player_ids, players_stat)
        return comparison

    def _dimension_evidence(self, player_ids, players_stat, dimension: str) -> dict:
        base_metrics = {
            "offense": ["goals", "assists", "points", "points_per_game"],
            "defense": ["plus_minus"],
            "puck_skill": ["shooting_pct"],
            "durability": ["games_played", "seasons_played"],
            "efficiency": ["points_per_game", "shooting_pct"],
        }
        metrics = base_metrics.get(dimension, ["points"])
        leaders = {}
        for m in metrics:
            values = {}
            for pid in player_ids:
                rs = (players_stat[pid].get("regular_season") or {}).get(m, 0)
                values[pid] = round(rs, 3) if rs is not None else None
            leaders[m] = values
        return {
            "metric": metrics,
            "values": leaders,
            "interpretation": self._dimension_interpretation(dimension),
        }

    def _comparison_notes(self, player_ids, players_stat) -> list[str]:
        notes = []
        if len(player_ids) < 2:
            return notes
        stats = [
            (players_stat[pid].get("regular_season") or {}).get("points") or 0
            for pid in player_ids
        ]
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
                "Raw offensive production. Which player generated more goals, "
                "assists, and points?"
            ),
            "defense": (
                "Available defensive evidence. Plus/minus reflects goal "
                "differential while on ice; it does not fully measure defensive "
                "reads or positioning."
            ),
            "puck_skill": (
                "Puck skill proxies available in the data. Shooting percentage, "
                "possession-based time on ice, and faceoff performance where "
                "present."
            ),
            "durability": "Games played and seasons sustained at the NHL level.",
            "efficiency": (
                "Production relative to opportunity: points per game and scoring "
                "efficiency."
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
        totals the leaderboards use.
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
        fields: list[str] = list(weights) if stat_type == "skater" else ["wins", "shutouts"]

        sums: dict[int, dict[str, float]] = {}
        games: dict[int, float] = {}
        recent_team: dict[int, str | None] = {}
        save_sums: dict[int, list[float]] = {}

        rows = (
            await self.session.execute(
                select(model).where(model.game_type == game_type)
            )
        ).scalars().all()

        for row in rows:
            pid = row.player_id
            if pid is None:
                continue
            bucket = sums.setdefault(pid, {f: 0.0 for f in fields})
            games[pid] = games.get(pid, 0.0) + (row.games_played or 0)
            if stat_type == "goalie":
                bb = save_sums.setdefault(pid, [0.0, 0.0])
                bb[0] += row.saves or 0
                bb[1] += row.shots_against or 0
            for f in fields:
                v = getattr(row, f, None)
                if v is not None:
                    bucket[f] += v
            if row.team_abbrevs:
                recent_team[pid] = row.team_abbrevs

        player_ids = list(sums)
        player_map: dict[int, Player] = {}
        if player_ids:
            players = (
                await self.session.execute(
                    select(Player).where(Player.id.in_(player_ids))
                )
            ).scalars().all()
            player_map = {p.id: p for p in players}

        pickable = []
        for pid, bucket in sums.items():
            fp = sum(bucket[f] * weights[f] for f in fields)
            save_pct = None
            if stat_type == "goalie":
                made, faced = save_sums[pid]
                if faced:
                    save_pct = made / faced
                    fp += (save_pct - 0.900) * weights.get("save_pct_bonus", 0.0)
            gp = games.get(pid, 0)
            metrics = {
                k: (round(v, 4) if isinstance(v, float) else v)
                for k, v in bucket.items()
            }
            if save_pct is not None:
                metrics["save_pct"] = round(save_pct, 4)
            player = player_map.get(pid)
            pickable.append(
                {
                    "player_id": pid,
                    "name": player.full_name if player else str(pid),
                    "team": recent_team.get(pid),
                    "position": player.position_code if player else None,
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
        rows = (
            await self.session.execute(
                select(model).where(model.game_type == game_type)
            )
        ).scalars().all()

        rate_sources = _RATE_METRICS.get((stat_type, metric))
        if min_games is None and rate_sources:
            min_games = _MIN_GAMES_IF_RATE

        # bucket = [value-or-rate-numerator, rate denominator, games played]
        buckets: dict[int, list[float]] = {}
        recent_team: dict[int, str | None] = {}
        for row in rows:
            player_id = row.player_id
            bucket = buckets.setdefault(player_id, [0.0, 0.0, 0.0])
            bucket[2] += row.games_played or 0
            if rate_sources:
                num, den, scale = rate_sources
                n = getattr(row, num)
                d = getattr(row, den)
                if n is None or d is None:
                    continue
                bucket[0] += n
                bucket[1] += d
            else:
                value = getattr(row, column)
                if value is None:
                    continue
                bucket[0] += value
            if row.team_abbrevs:
                recent_team[player_id] = row.team_abbrevs

        qualified = []
        for player_id, (num, den, games) in buckets.items():
            if min_games is not None and games < min_games:
                continue
            if rate_sources:
                _, _, scale = rate_sources
                value = num * scale / den if den else None
            else:
                value = num
            qualified.append((player_id, value))

        player_ids = [pid for pid, _ in qualified]
        player_map: dict[int, Player] = {}
        if player_ids:
            players = (
                await self.session.execute(
                    select(Player).where(Player.id.in_(player_ids))
                )
            ).scalars().all()
            player_map = {p.id: p for p in players}

        qualified.sort(key=lambda t: t[1], reverse=True)

        ranked = []
        for idx, (player_id, value) in enumerate(qualified, start=1):
            player = player_map.get(player_id)
            ranked.append(
                {
                    "rank": idx,
                    "player_id": player_id,
                    "name": player.full_name if player else str(player_id),
                    "team": recent_team.get(player_id),
                    "position": player.position_code if player else None,
                    "value": round(value, 4) if isinstance(value, float) else value,
                }
            )
        return ranked[: self._leaderboard_cutoff(ranked, limit)]
