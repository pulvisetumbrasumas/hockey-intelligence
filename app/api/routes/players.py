from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models import Player, Team
from app.schemas.common import PlayerOut, PlayerSearchResult, SearchResponse


router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def global_search(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Global search across players and teams."""
    term = f"%{q}%"
    player_result = await db.execute(
        select(Player)
        .where(
            Player.full_name.ilike(term)
            | Player.first_name.ilike(term)
            | Player.last_name.ilike(term)
            | Player.position_code.ilike(term)
        )
        .order_by(Player.full_name)
        .limit(limit)
    )
    players = player_result.scalars().all()

    team_result = await db.execute(
        select(Team)
        .where(Team.full_name.ilike(term) | Team.city.ilike(term) | Team.abbreviation.ilike(term))
        .order_by(Team.full_name)
        .limit(limit)
    )
    teams = team_result.scalars().all()

    return SearchResponse(
        query=q,
        players=[
            PlayerSearchResult(
                player_id=p.id,
                full_name=p.full_name,
                position=p.position_code,
                active=bool(p.active),
            )
            for p in players
        ],
        teams=[
            {
                "team_id": t.id,
                "full_name": t.full_name,
                "abbreviation": t.abbreviation,
                "active": bool(t.active),
            }
            for t in teams
        ],
        count=len(players) + len(teams),
    )


@router.get("/players/{player_id}", response_model=PlayerOut)
async def get_player(player_id: int, db: AsyncSession = Depends(get_db)):
    player = await db.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found.")
    return PlayerOut(
        player_id=player.id,
        full_name=player.full_name,
        position=player.position_code,
        birth_date=player.birth_date.strftime("%Y-%m-%d") if player.birth_date else None,
        birth_city=player.birth_city,
        birth_country=player.birth_country,
        height=player.height,
        weight=player.weight,
        shoots_catches=player.shoots_catches,
        draft_year=player.draft_year,
        draft_round=player.draft_round,
        draft_overall=player.draft_overall,
        active=bool(player.active),
    )


@router.get("/players/search/{query}", response_model=list[PlayerSearchResult])
async def search_players(
    query: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    term = f"%{query}%"
    result = await db.execute(
        select(Player)
        .where(
            Player.full_name.ilike(term)
            | Player.first_name.ilike(term)
            | Player.last_name.ilike(term)
        )
        .order_by(Player.full_name)
        .limit(limit)
    )
    return [
        PlayerSearchResult(
            player_id=p.id,
            full_name=p.full_name,
            position=p.position_code,
            active=bool(p.active),
        )
        for p in result.scalars().all()
    ]