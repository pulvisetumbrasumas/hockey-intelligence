"""Per-team / per-franchise season history engine.

Builds a chronological series of a club's regular-season records from
team_season_stats, markers it with championship and conference-final
appearances, and derives deterministic records and streaks. All offline —
no external data required.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Champion, PlayoffSeries, Season, Team, TeamSeasonStats


def _season_row(stats: TeamSeasonStats, label: str | None, team: Team | None) -> dict:
    gp = cast(int, stats.games_played) or 0
    pts = cast(int, stats.points) or 0
    gf = cast(int, stats.goals_for) or 0
    ga = cast(int, stats.goals_against) or 0
    return {
        "season_id": stats.season_id,
        "season_label": label or str(stats.season_id),
        "team_id": stats.team_id,
        "team_name": team.full_name if team else None,
        "games_played": gp,
        "wins": cast(int, stats.wins) or 0,
        "losses": cast(int, stats.losses) or 0,
        "ot_losses": cast(int, stats.ot_losses) or 0,
        "ties": cast(int, stats.ties) or 0,
        "points": pts,
        "goals_for": gf,
        "goals_against": ga,
        "goal_differential": gf - ga,
        "points_pct": round(pts / (gp * 2), 3) if gp else 0.0,
        "stanley_cup": False,
        "cup_finalist": False,
        "conference_final": False,
    }


def _best(rows: list[dict], key: str) -> dict | None:
    candidates = [r for r in rows if r.get(key) is not None]
    if not candidates:
        return None
    top = max(candidates, key=lambda r: r[key])
    tied = [r for r in candidates if r[key] == top[key]]
    return {
        "season_id": top["season_id"],
        "season_label": top.get("season_label"),
        "value": top[key],
        "count": len(tied),
    }


_INDEXED = ("points", "wins", "points_pct")


def summarize_history(rows: list[dict]) -> dict:
    """Deterministic records + streaks from ascending per-season rows.

    Pure function — rows are the dicts produced by build_team_season_history,
    in ascending season order. Tests rely on its exact behaviour.
    """
    records: dict[str, dict | None] = {}
    for key in _INDEXED:
        records[key] = _best(rows, key)

    def runs_of(predicate) -> tuple[int, int]:
        longest = current = 0
        for row in rows:
            if predicate(row):
                current += 1
                longest = max(longest, current)
            else:
                current = 0
        return longest, current

    longest_500, current_500 = runs_of(lambda r: r["points_pct"] >= 0.5)
    longest_100, current_100 = runs_of(lambda r: r["points"] >= 100)

    cup_seasons = [r["season_id"] for r in rows if r["stanley_cup"]]
    last_cup = cup_seasons[-1] if cup_seasons else None
    seasons_since_cup = None
    if last_cup is not None and rows:
        idx_cup = next(i for i, r in enumerate(rows) if r["season_id"] == last_cup)
        seasons_since_cup = len(rows) - 1 - idx_cup

    return {
        "records": records,
        "streaks": {
            "longest_winning_seasons": longest_500,
            "current_winning_seasons": current_500,
            "longest_100_point_seasons": longest_100,
            "current_100_point_seasons": current_100,
            "seasons_since_cup": seasons_since_cup,
            "last_cup_season": last_cup,
        },
    }


async def build_team_season_history(
    db: AsyncSession, team_ids: set[int], scope: str = "team"
) -> dict:
    """Chronological club/franchise record with championship markers."""
    ids = sorted(team_ids)
    rows = (
        await db.execute(
            select(TeamSeasonStats, Season.formatted_id, Team)
            .join(Season, Season.id == TeamSeasonStats.season_id)
            .join(Team, Team.id == TeamSeasonStats.team_id)
            .where(
                TeamSeasonStats.team_id.in_(ids),
                TeamSeasonStats.game_type == 2,
            )
            .order_by(TeamSeasonStats.season_id.asc())
        )
    ).all()
    seasons = [_season_row(stats, label, team) for stats, label, team in rows]
    by_season = {row["season_id"]: row for row in seasons}

    champ_q = await db.execute(
        select(Champion).where(
            Champion.winner_team_id.in_(ids) | Champion.runner_team_id.in_(ids)
        )
    )
    for champ in champ_q.scalars():
        row = by_season.get(champ.season_id)
        if not row:
            continue
        if champ.winner_team_id in ids:
            row["stanley_cup"] = True
            row["cup_finalist"] = True
        if champ.runner_team_id in ids:
            row["cup_finalist"] = True

    series_q = await db.execute(
        select(PlayoffSeries).where(
            PlayoffSeries.winner_team_id.in_(ids)
            | PlayoffSeries.loser_team_id.in_(ids)
        )
    )
    for series in series_q.scalars():
        row = by_season.get(series.season_id)
        if row and (series.winner_team_id in ids or series.loser_team_id in ids):
            row["conference_final"] = True

    return {
        "scope": scope,
        "team_ids": ids,
        "seasons": seasons,
        **summarize_history(seasons),
    }
