from __future__ import annotations

import time
from datetime import UTC, date, datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.connection import get_db
from app.models import Season, Team
from app.models.stats_team import TeamSeasonStats
from app.services.images import team_logo_url

router = APIRouter(prefix="/api", tags=["platform"])

_CACHE: dict[str, tuple[float, object]] = {}


def _cached(key: str, ttl: int) -> object | None:
    entry = _CACHE.get(key)
    if entry and time.time() - entry[0] < ttl:
        return entry[1]
    return None


def _store(key: str, value: object) -> object:
    _CACHE[key] = (time.time(), value)
    return value


async def _web_json(path: str, params: dict | None = None) -> dict:
    settings = get_settings()
    url = f"{settings.nhl_web_api_base}/{path}"
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise HTTPException(status_code=502, detail="Unexpected NHL API response.")
        return data


def _normalize_team(team: dict, h_score: int | None, a_score: int | None) -> dict:
    abbr = (team.get("abbrev") or "").upper() or team.get("tricode") or ""
    name = team.get("placeName", {}).get("default", "") if isinstance(
        team.get("placeName"), dict
    ) else ""
    common = team.get("commonName", {}).get("default", "") if isinstance(
        team.get("commonName"), dict
    ) else ""
    return {
        "id": team.get("id"),
        "abbreviation": abbr,
        "name": f"{name} {common}".strip(),
        "score": h_score is not None and team.get("score") or team.get("score"),
        "logo": team_logo_url(abbr),
        "record": team.get("record"),
    }


def _normalize_games(payload: dict) -> list[dict]:
    games: list[dict] = []
    today = payload.get("nextStartDate") or ""
    for week in payload.get("gameWeek", []):
        for g in week.get("games", []):
            start = g.get("startTimeUTC", "")
            games.append(
                {
                    "game_id": g.get("id"),
                    "game_type": g.get("gameType") or "",
                    "state": g.get("gameState") or "",
                    "period": g.get("periodDescriptor", {}).get("number"),
                    "clock": g.get("clock", {}).get("timeRemaining"),
                    "start_time_utc": start,
                    "eastern_time": g.get("startTimeEastern") or _eastern(start),
                    "in_series": g.get("seriesStatus", {}).get("isSeries"),
                    "series_game": g.get("seriesStatus", {}).get("gameInSeries")
                    if isinstance(g.get("seriesStatus"), dict)
                    else None,
                    "season": g.get("season", today),
                    "away": _normalize_team(
                        g.get("awayTeam", {}),
                        g.get("awayTeam", {}).get("score"),
                        g.get("homeTeam", {}).get("score"),
                    ),
                    "home": _normalize_team(
                        g.get("homeTeam", {}),
                        g.get("awayTeam", {}).get("score"),
                        g.get("homeTeam", {}).get("score"),
                    ),
                }
            )
    return games


def _eastern(utc: str) -> str:
    try:
        dt = datetime.fromisoformat(utc.replace("Z", "+00:00"))
    except Exception:
        return utc
    ny = timezone(timedelta(hours=-4))
    return dt.astimezone(ny).strftime("%I:%M %p")


async def _season_facts_from_nhl(db: AsyncSession) -> dict:
    cached = _cached("season-facts", get_settings().season_facts_cache_ttl)
    if cached:
        return cached  # type: ignore[no-any-return]

    today = date.today().isoformat()
    try:
        payload = await _web_json(f"schedule/{today}")
        facts = {
            "cursor_date": today,
            "regular_season": {
                "start": payload.get("regularSeasonStartDate"),
                "end": payload.get("regularSeasonEndDate"),
            },
            "playoff_end": payload.get("playoffEndDate"),
            "preseason": {
                "start": payload.get("preSeasonStartDate"),
            },
        }
    except Exception:
        settings = get_settings()
        facts = {
            "cursor_date": today,
            "regular_season": {
                "start": settings.countdown_target_fallback,
                "end": None,
            },
            "playoff_end": None,
            "preseason": {"start": None},
        }

    result = await db.execute(
        select(
            func.max(Season.total_regular_season_games),
            func.count(Season.id),
        )
    )
    total_games, tracked = result.one()
    facts["league"] = {
        "teams": 32,
        "regular_season_games": total_games or 1312,
        "seasons_tracked": tracked or 0,
    }
    return _store("season-facts", facts)  # type: ignore[return-value]


@router.get("/season-facts")
async def season_facts(db: AsyncSession = Depends(get_db)):
    """Data-driven season countdown facts (NHL schedule API + database)."""
    return await _season_facts_from_nhl(db)


@router.get("/events")
async def events(db: AsyncSession = Depends(get_db)):
    """Upcoming league-wide events. Date sources marked per event."""
    settings = get_settings()
    facts = await _season_facts_from_nhl(db)
    now = time.time()

    def entry(key: str, title: str, date_str: str | None, source: str) -> dict:
        target = _ts(date_str)
        return {
            "id": key,
            "title": title,
            "date": date_str,
            "source": source,
            "is_past": target is not None and target < now,
            "countdown_seconds": max(target - now, 0) if target else None,
        }

    items = [
        entry(
            "preseason",
            "Preseason opens",
            facts["preseason"].get("start"),
            "NHL schedule API",
        ),
        entry(
            "regular-season",
            "2026-27 regular season begins",
            facts["regular_season"].get("start"),
            "NHL schedule API",
        ),
        entry(
            "regular-season-end",
            "2026-27 regular season ends",
            facts["regular_season"].get("end"),
            "NHL schedule API",
        ),
        entry("playoff-end", "Stanley Cup Final window", facts["playoff_end"], "NHL schedule API"),
        entry(
            "trade-deadline",
            "Trade deadline",
            settings.trade_deadline_date,
            "configured",
        ),
        entry("draft", "NHL Draft", settings.nhl_draft_date, "configured"),
        entry("all-star", "NHL All-Star weekend", settings.all_star_date, "configured"),
    ]
    return {"season": facts, "events": items}


def _ts(date_str: str | None) -> float | None:
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str)
    except Exception:
        try:
            dt = datetime.fromisoformat(date_str)
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.timestamp()


@router.get("/seasons")
async def seasons(db: AsyncSession = Depends(get_db)):
    """Seasons tracked in the database (most recent first)."""
    rows = (
        await db.execute(
            select(Season).order_by(Season.id.desc()).limit(120)
        )
    ).scalars().all()
    return {
        "seasons": [
            {
                "season_id": s.id,
                "label": s.formatted_id or str(s.id),
                "start_date": s.start_date.strftime("%Y-%m-%d") if s.start_date else None,
                "regular_season_end": (
                    s.regular_season_end_date.strftime("%Y-%m-%d")
                    if s.regular_season_end_date
                    else None
                ),
                "total_regular_season_games": s.total_regular_season_games,
                "regular_season_games": s.regular_season_games,
                "number_of_teams": s.number_of_teams,
            }
            for s in rows
        ]
    }


@router.get("/schedule")
async def schedule(
    day_key: str = Query("today", alias="date", pattern=r"^(today|next|\d{4}-\d{2}-\d{2})$"),
    db: AsyncSession = Depends(get_db),
):
    """Date-scoped games from the live NHL schedule, normalized for the UI."""
    _ = db
    day = day_key
    if day == "today":
        day = datetime.now(UTC).date().isoformat()
    if day == "next":
        sp = await _web_json(f"schedule/{datetime.now(UTC).date().isoformat()}")
        day = sp.get("nextStartDate") or day
    payload = await _web_json(f"schedule/{day}")
    return {
        "date": day,
        "next_start_date": payload.get("nextStartDate"),
        "games": _normalize_games(payload),
    }


@router.get("/standings")
async def standings(
    season_id: int = Query(20242025),
    game_type: int = Query(2, ge=2, le=3),
    db: AsyncSession = Depends(get_db),
):
    """League standings computed from the database (team_season_stats)."""
    rows = (
        await db.execute(
            select(TeamSeasonStats, Team, Season.formatted_id)
            .join(Team, Team.id == TeamSeasonStats.team_id)
            .join(Season, Season.id == TeamSeasonStats.season_id)
            .where(
                TeamSeasonStats.season_id == season_id,
                TeamSeasonStats.game_type == game_type,
            )
        )
    ).all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No standings for season {season_id}.")

    standings_rows: list[dict] = []
    for stats, team, _ in rows:
        gp = stats.games_played or 0
        pts = stats.points or 0
        standings_rows.append(
            {
                "team_id": stats.team_id,
                "name": team.full_name,
                "abbreviation": team.abbreviation,
                "logo": team_logo_url(team.abbreviation),
                "games_played": gp,
                "wins": stats.wins or 0,
                "losses": stats.losses or 0,
                "ot_losses": stats.ot_losses or 0,
                "ties": stats.ties or 0,
                "points": pts,
                "goals_for": stats.goals_for or 0,
                "goals_against": stats.goals_against or 0,
                "goal_differential": (stats.goals_for or 0) - (stats.goals_against or 0),
                "points_pct": round(pts / (gp * 2), 3) if gp else 0.0,
                "row": (stats.wins or 0) + (stats.ot_losses or 0),
                "reg_wins": stats.wins or 0,
            }
        )
    standings_rows.sort(
        key=lambda r: (r["points"], r["reg_wins"], r["goal_differential"]), reverse=True
    )
    for index, row in enumerate(standings_rows, start=1):
        row["rank"] = index
        row["in_playoffs"] = index <= 16
    return {
        "season_id": season_id,
        "season_label": rows[0][1],
        "game_type": game_type,
        "note": "League-wide view sorted by points; conference splits return in a later slice.",
        "rows": standings_rows,
    }
