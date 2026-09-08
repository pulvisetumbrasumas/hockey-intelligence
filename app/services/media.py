"""Player/team media lookups used by the API layer.

Keeps image URLs derived from committed database values rather than making
requests to the NHL API per player.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stats import PlayerSeasonStats
from app.services.images import player_headshot_url, player_hero_url


async def latest_team_by_player(
    db: AsyncSession, player_ids: list[int]
) -> dict[int, dict]:
    """Most recent regular-season team abbreviation + media URLs per player id."""
    out: dict[int, dict] = {}
    if not player_ids:
        return out

    latest_season = (
        select(
            PlayerSeasonStats.player_id.label("player_id"),
            PlayerSeasonStats.season_id.label("season_id"),
        )
        .where(
            PlayerSeasonStats.player_id.in_(player_ids),
            PlayerSeasonStats.game_type == 2,
        )
        .group_by(PlayerSeasonStats.player_id)
        .subquery()
    )

    rows = (
        await db.execute(
            select(
                PlayerSeasonStats.player_id.label("player_id"),
                PlayerSeasonStats.team_abbrevs.label("team_abbrevs"),
            )
            .join(
                latest_season,
                (PlayerSeasonStats.player_id == latest_season.c.player_id)
                & (PlayerSeasonStats.season_id == latest_season.c.season_id),
            )
            .where(PlayerSeasonStats.game_type == 2)
        )
    ).all()

    for row in rows:
        abbr = (row.team_abbrevs or "").split(",")[0].strip() or None
        out[row.player_id] = {
            "team_abbreviation": abbr,
            "headshot": player_headshot_url(row.player_id, abbr),
            "hero": player_hero_url(row.player_id),
        }
    return out
