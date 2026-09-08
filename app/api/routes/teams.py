from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models import Champion, Franchise, Season, Team, TeamIdentity
from app.schemas.common import TeamOut
from app.services.images import team_logo_url

router = APIRouter(prefix="/api", tags=["teams"])


def _championships_rows(champion: Champion, season_label: str, ids: set[int]) -> dict | None:
    won = champion.winner_team_id in ids
    involved = won or champion.runner_team_id in ids
    if not involved:
        return None
    return {
        "season_id": champion.season_id,
        "season_label": season_label,
        "won": won,
        "champion": champion.winner_name,
        "runner_up": champion.runner_name,
        "champ_wins": champion.champ_wins,
        "runner_wins": champion.runner_wins,
        "note": champion.note,
    }


@router.get("/franchises")
async def list_franchises(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Franchise, func.count(TeamIdentity.id))
        .outerjoin(TeamIdentity, TeamIdentity.franchise_id == Franchise.id)
        .group_by(Franchise.id)
        .order_by(Franchise.full_name)
    )
    rows = result.all()
    return [
        {
            "franchise_id": f.id,
            "full_name": f.full_name,
            "common_name": f.common_name,
            "place_name": f.place_name,
            "established_year": f.established_year,
            "active": bool(f.active),
            "successor_franchise_id": f.successor_franchise_id,
            "identity_count": count,
        }
        for f, count in rows
    ]


@router.get("/franchises/{franchise_id}")
async def get_franchise(franchise_id: int, db: AsyncSession = Depends(get_db)):
    franchise = await db.get(Franchise, franchise_id)
    if not franchise:
        raise HTTPException(status_code=404, detail=f"Franchise {franchise_id} not found.")
    identities = (
        await db.execute(
            select(TeamIdentity)
            .where(TeamIdentity.franchise_id == franchise.id)
            .order_by(TeamIdentity.start_year)
        )
    ).scalars().all()
    return {
        "franchise_id": franchise.id,
        "full_name": franchise.full_name,
        "common_name": franchise.common_name,
        "place_name": franchise.place_name,
        "established_year": franchise.established_year,
        "active": bool(franchise.active),
        "successor_franchise_id": franchise.successor_franchise_id,
        "notes": franchise.notes,
        "identities": [
            {
                "team_id": i.team_id,
                "name": i.name,
                "city": i.city,
                "abbr": i.abbr,
                "start_year": i.start_year,
                "end_year": i.end_year,
                "notes": i.notes,
            }
            for i in identities
        ],
    }
@router.get("/teams/{team_id}")
async def get_team(team_id: int, db: AsyncSession = Depends(get_db)):
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found.")
    identity_rows = await db.execute(
        select(TeamIdentity).where(TeamIdentity.team_id == team.id)
    )
    identities = [
        {
            "name": i.name,
            "city": i.city,
            "abbr": i.abbr,
            "start_year": i.start_year,
            "end_year": i.end_year,
        }
        for i in identity_rows.scalars()
    ]
    identity_ids = {team.id}
    franchise: dict | None = None
    if team.franchise_id:
        franchise_row = await db.get(Franchise, team.franchise_id)
        if franchise_row:
            franchise = {"id": franchise_row.id, "name": franchise_row.full_name}
        siblings = (
            await db.execute(select(Team.id).where(Team.franchise_id == team.franchise_id))
        ).scalars().all()
        identity_ids.update(siblings)
    champ_rows = (
        await db.execute(
            select(Champion, Season.formatted_id)
            .join(Season, Season.id == Champion.season_id)
            .order_by(Season.id.desc())
        )
    ).all()
    championships: list[dict] = []
    cup_count = 0
    for champion, label in champ_rows:
        row = _championships_rows(champion, label or str(champion.season_id), identity_ids)
        if row:
            championships.append(row)
            if row["won"]:
                cup_count += 1
    return TeamOut(
        team_id=team.id,
        full_name=team.full_name,
        abbreviation=team.abbreviation,
        franchise=franchise,
        active=bool(team.active),
        identities=identities,
        championships=championships,
        cup_count=cup_count,
    )


@router.get("/teams")
async def list_teams(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team).order_by(Team.full_name))
    teams = result.scalars().all()
    return [
        {
            "team_id": t.id,
            "full_name": t.full_name,
            "abbreviation": t.abbreviation,
            "tricode": t.tricode,
            "active": bool(t.active),
            "logo": team_logo_url(t.abbreviation),
            "first_season_id": t.first_season_id,
        }
        for t in teams
    ]
