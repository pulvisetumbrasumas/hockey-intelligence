from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models import Franchise, Player, Team
from app.schemas.common import PlayerOut, PlayerSearchResult, SearchResponse
from app.services.images import team_logo_url
from app.services.media import latest_team_by_player

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

    franchise_result = await db.execute(
        select(Franchise)
        .where(
            Franchise.full_name.ilike(term)
            | Franchise.common_name.ilike(term)
            | Franchise.place_name.ilike(term)
        )
        .order_by(Franchise.full_name)
        .limit(limit)
    )
    franchises = franchise_result.scalars().all()

    media = await latest_team_by_player(db, [p.id for p in players])
    return SearchResponse(
        query=q,
        players=[
            PlayerSearchResult(
                player_id=p.id,
                full_name=p.full_name,
                position=p.position_code,
                active=bool(p.active),
                nhl_id=p.nhl_id,
                headshot=media.get(p.id, {}).get("headshot"),
                hero=media.get(p.id, {}).get("hero"),
                team_abbreviation=media.get(p.id, {}).get("team_abbreviation"),
            )
            for p in players
        ],
        teams=[
            {
                "team_id": t.id,
                "full_name": t.full_name,
                "abbreviation": t.abbreviation,
                "active": bool(t.active),
                "logo": team_logo_url(t.abbreviation),
            }
            for t in teams
        ],
        franchises=[
            {
                "franchise_id": f.id,
                "full_name": f.full_name,
                "established_year": f.established_year,
                "active": bool(f.active),
            }
            for f in franchises
        ],
        count=len(players) + len(teams) + len(franchises),
    )


@router.get("/players/{player_id}", response_model=PlayerOut)
async def get_player(player_id: int, db: AsyncSession = Depends(get_db)):
    player = await db.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found.")
    media = (await latest_team_by_player(db, [player.id])) or {}
    media_row = media.get(player.id, {})
    return PlayerOut(
        player_id=player.id,
        full_name=player.full_name,
        position=player.position_code,
        nhl_id=player.nhl_id,
        headshot=media_row.get("headshot"),
        hero=media_row.get("hero"),
        team_abbreviation=media_row.get("team_abbreviation"),
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
    players = result.scalars().all()
    media = await latest_team_by_player(db, [p.id for p in players])
    return [
        PlayerSearchResult(
            player_id=p.id,
            full_name=p.full_name,
            position=p.position_code,
            active=bool(p.active),
            nhl_id=p.nhl_id,
            headshot=media.get(p.id, {}).get("headshot"),
            hero=media.get(p.id, {}).get("hero"),
            team_abbreviation=media.get(p.id, {}).get("team_abbreviation"),
        )
        for p in players
    ]
