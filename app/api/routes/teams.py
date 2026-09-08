from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models import Team
from app.schemas.common import TeamOut

router = APIRouter(prefix="/api", tags=["teams"])


@router.get("/teams/{team_id}", response_model=TeamOut)
async def get_team(team_id: int, db: AsyncSession = Depends(get_db)):
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found.")
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
    return TeamOut(
        team_id=team.id,
        full_name=team.full_name,
        abbreviation=team.abbreviation,
        franchise=franchise,
        active=bool(team.active),
        identities=identities,
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
            "active": bool(t.active),
        }
        for t in teams
    ]
