from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models import Player
from app.models.stats import PlayerSeasonStats
from app.services.statistics.engine import StatisticsEngine

router = APIRouter(prefix="/api", tags=["statistics"])


@router.get("/stats/leaders/season/{season_id}")
async def season_leaders(
    season_id: int,
    metric: str = Query("points"),
    game_type: int = Query(2, ge=2, le=3),
    stat_type: str = Query("skater", pattern="^(skater|goalie)$"),
    limit: int = Query(10, ge=1, le=100),
    min_games: int | None = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Leaderboard for a single season."""
    engine = StatisticsEngine(db)
    try:
        return await engine.get_leaderboard(
            season_id=season_id,
            metric=metric,
            game_type=game_type,
            stat_type=stat_type,
            limit=limit,
            min_games=min_games,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/stats/leaders/career")
async def career_leaders(
    metric: str = Query("points"),
    game_type: int = Query(2, ge=2, le=3),
    stat_type: str = Query("skater", pattern="^(skater|goalie)$"),
    limit: int = Query(10, ge=1, le=100),
    min_games: int | None = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
):
    """All-time career leaderboard (grouped across seasons)."""
    engine = StatisticsEngine(db)
    try:
        return await engine.get_leaderboard(
            season_id=None,
            metric=metric,
            game_type=game_type,
            stat_type=stat_type,
            limit=limit,
            min_games=min_games,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/players/{player_id}/career")
async def player_career_stats(player_id: int, db: AsyncSession = Depends(get_db)):
    """Career totals computed deterministically by the statistics engine."""
    engine = StatisticsEngine(db)
    stats = await engine.get_player_career_stats(player_id)
    if not stats.get("regular_season"):
        # Nothing aggregated; confirm the player exists
        player = await db.get(Player, player_id)
        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found.")
    return stats


@router.get("/players/{player_id}/season/{season_id}")
async def player_season_stats(
    player_id: int, season_id: int, db: AsyncSession = Depends(get_db)
):
    engine = StatisticsEngine(db)
    stats = await engine.get_player_season_stats(player_id, season_id)
    if stats is None:
        raise HTTPException(
            status_code=404,
            detail=f"No statistics found for player {player_id} in season {season_id}.",
        )
    return stats


@router.get("/players/{player_id}/seasons")
async def player_season_list(
    player_id: int,
    game_type: int = Query(2, ge=2, le=3),
    db: AsyncSession = Depends(get_db),
):
    """Per-season breakdown for a player."""
    player = await db.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found.")
    result = await db.execute(
        select(PlayerSeasonStats)
        .where(
            PlayerSeasonStats.player_id == player_id,
            PlayerSeasonStats.game_type == game_type,
        )
        .order_by(PlayerSeasonStats.season_id)
    )
    rows = result.scalars().all()
    return {
        "player_id": player_id,
        "name": player.full_name,
        "game_type": game_type,
        "seasons": [
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
            for r in rows
        ],
    }


@router.post("/compare/players")
async def compare_players(
    player_ids: list[int] = Query(..., min_length=2, max_length=5),
    dimensions: list[str] | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Multi-dimensional player comparison. Never declares a single winner."""
    engine = StatisticsEngine(db)
    return await engine.compare_players(player_ids, dimensions)
