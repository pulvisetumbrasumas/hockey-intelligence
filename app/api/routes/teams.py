from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models import Champion, Franchise, Game, Season, Team, TeamIdentity
from app.schemas.common import TeamOut
from app.services.history import build_team_season_history
from app.services.images import team_logo_url
from app.services.streaks import compute_team_streaks, team_game_views

router = APIRouter(prefix="/api", tags=["teams"])


def _team_lite(team: Team | None) -> dict | None:
    if not team:
        return None
    return {
        "team_id": team.id,
        "name": team.full_name,
        "abbreviation": team.abbreviation,
        "logo": team_logo_url(team.abbreviation),
    }


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


async def _sibling_ids(db: AsyncSession, franchise_id: int) -> set[int]:
    result = await db.execute(select(Team.id).where(Team.franchise_id == franchise_id))
    return set(result.scalars().all())


@router.get("/teams/{team_id}/seasons")
async def team_season_history(team_id: int, db: AsyncSession = Depends(get_db)):
    """Per-season record chart for one club (franchise lineage included)."""
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found.")
    ids = {team.id}
    if team.franchise_id:
        ids.update(await _sibling_ids(db, team.franchise_id))
    history = await build_team_season_history(db, ids, scope="team")
    history["team_id"] = team.id
    history["full_name"] = team.full_name
    history["abbreviation"] = team.abbreviation
    history["logo"] = team_logo_url(team.abbreviation)
    return history


async def _covered_seasons(
    db: AsyncSession, team_id: int
) -> list[dict]:
    """Seasons that have at least one stored game for the team, newest first."""
    rows = (
        await db.execute(
            select(Game.season_id, Season.formatted_id, func.count(Game.id))
            .join(Season, Season.id == Game.season_id)
            .where(or_(Game.home_team_id == team_id, Game.away_team_id == team_id))
            .group_by(Game.season_id, Season.formatted_id)
            .order_by(Game.season_id.desc())
        )
    ).all()
    return [
        {"season_id": sid, "season_label": label, "games": count}
        for sid, label, count in rows
    ]


def _game_row(
    game: Game,
    season_label: str,
    team_id: int,
    team_by_id: dict[int, Team],
) -> dict:
    is_home = game.home_team_id == team_id
    opponent_id = game.away_team_id if is_home else game.home_team_id
    opponent = team_by_id.get(opponent_id) if opponent_id is not None else None
    team_score = getattr(game, "home_score" if is_home else "away_score")
    opponent_score = getattr(game, "away_score" if is_home else "home_score")
    if team_score is None or opponent_score is None:
        result = None
    elif team_score > opponent_score:
        result = "W"
    else:
        result = "OTL" if game.ot_sol else "L"
    return {
        "game_id": game.id,
        "season_id": game.season_id,
        "season_label": season_label,
        "game_date": game.game_date.isoformat() if game.game_date else None,
        "game_type": game.game_type,
        "is_home": is_home,
        "opponent": _team_lite(opponent),
        "team_score": team_score,
        "opponent_score": opponent_score,
        "result": result,
        "ot": game.ot_sol,
        "venue": game.venue,
    }


@router.get("/teams/{team_id}/games")
async def team_games(
    team_id: int,
    season_id: int | None = Query(None),
    limit: int = Query(20, ge=1, le=120),
    db: AsyncSession = Depends(get_db),
):
    """Game log and game-level streaks for one club.

    Without a ``season_id`` the most recent season with stored games is used.
    Streaks are computed over regular-season games only (game_type 2).
    """
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found.")

    coverage = await _covered_seasons(db, team_id)
    if not coverage:
        return {
            "team_id": team.id,
            "team_name": team.full_name,
            "abbreviation": team.abbreviation,
            "logo": team_logo_url(team.abbreviation),
            "coverage": [],
            "season_id": None,
            "games": [],
            "streaks": None,
        }
    effective = season_id or coverage[0]["season_id"]

    season_map = {c["season_id"]: c["season_label"] for c in coverage}
    rows = (
        await db.execute(
            select(Game, Season.formatted_id)
            .join(Season, Season.id == Game.season_id)
            .where(
                or_(Game.home_team_id == team_id, Game.away_team_id == team_id),
                Game.season_id == effective,
            )
            .order_by(Game.game_date.asc(), Game.id.asc())
        )
    ).all()
    recent_rows = rows[-limit:] if limit else rows

    opponent_ids = {
        (g.away_team_id if g.home_team_id == team_id else g.home_team_id)
        for g, _ in recent_rows
        if g.home_team_id is not None and g.away_team_id is not None
    }
    team_by_id: dict[int, Team] = {}
    if opponent_ids:
        team_q = await db.execute(select(Team).where(Team.id.in_(opponent_ids)))
        team_by_id = {t.id: t for t in team_q.scalars()}

    recent = [
        _game_row(g, label or str(g.season_id), team_id, team_by_id)
        for g, label in recent_rows
    ]

    streak_dicts = []
    for g, _ in rows:
        if g.game_type != 2:
            continue
        streak_dicts.append(
            {
                "game_id": g.id,
                "game_date": g.game_date,
                "season_id": g.season_id,
                "game_type": g.game_type,
                "home_team_id": g.home_team_id,
                "away_team_id": g.away_team_id,
                "home_score": g.home_score,
                "away_score": g.away_score,
                "ot_sol": g.ot_sol,
            }
        )
    streaks = (
        compute_team_streaks(team_game_views(streak_dicts, team_id))
        if streak_dicts
        else None
    )

    return {
        "team_id": team.id,
        "team_name": team.full_name,
        "abbreviation": team.abbreviation,
        "logo": team_logo_url(team.abbreviation),
        "coverage": coverage,
        "season_id": effective,
        "season_label": season_map.get(effective),
        "games": recent,
        "streaks": streaks,
    }


@router.get("/franchises/{franchise_id}/seasons")
async def franchise_season_history(
    franchise_id: int, db: AsyncSession = Depends(get_db)
):
    """Per-season record chart across a franchise's full identity lineage."""
    franchise = await db.get(Franchise, franchise_id)
    if not franchise:
        raise HTTPException(status_code=404, detail=f"Franchise {franchise_id} not found.")
    ids = await _sibling_ids(db, franchise_id)
    if not ids:
        return {
            "scope": "franchise",
            "franchise_id": franchise.id,
            "full_name": franchise.full_name,
            "seasons": [],
            "records": {},
            "streaks": {},
        }
    history = await build_team_season_history(db, ids, scope="franchise")
    history["franchise_id"] = franchise.id
    history["full_name"] = franchise.full_name
    return history
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
