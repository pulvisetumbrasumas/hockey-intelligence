from __future__ import annotations

import asyncio
import time
from datetime import UTC, date, datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.connection import get_db
from app.models import Champion, PlayoffSeries, Player, PlayerSeasonStats, Season, Team
from app.models.stats_team import TeamSeasonStats
from app.services.images import team_logo_url
from app.services.statistics.engine import FANTASY_PRESETS, StatisticsEngine

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


async def _web_json(
    path: str, params: dict | None = None, base: str | None = None
) -> dict:
    settings = get_settings()
    url = f"{base or settings.nhl_web_api_base}/{path}"
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
    return await _events_payload(db)


async def _events_payload(db: AsyncSession) -> dict:
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


async def _normalize_espn_news(payload: dict) -> list[dict]:
    """Flatten ESPN NHL news articles into the UI's card shape."""
    items = []
    for a in payload.get("articles", []):
        categories = [c.get("description") or "" for c in a.get("categories", [])]
        categories = [c for c in categories if c]
        image = ""
        for img in a.get("images", []) or []:
            url = img.get("url")
            if url and img.get("type") in ("header", "full", None):
                image = url
                break
        link = ""
        for name in ("web", "desktop", "mobile"):
            node = a.get("links", {}).get(name)
            href = node.get("href") if isinstance(node, dict) else None
            if href and "espn" in href:
                link = href
                break
        items.append(
            {
                "id": a.get("id") or a.get("contentKey"),
                "title": a.get("headline"),
                "summary": a.get("description"),
                "byline": a.get("byline"),
                "published": a.get("published"),
                "category": categories[0] if categories else "NHL",
                "tags": categories,
                "image": image or "",
                "link": link or "",
                "premium": bool(a.get("premium")),
            }
        )
    return items


@router.get("/news")
async def news(db: AsyncSession = Depends(get_db)):
    """League headlines from the public ESPN NHL news feed."""
    _ = db
    settings = get_settings()
    cached = _cached("espn-news", settings.news_cache_ttl)
    if cached:
        return cached  # type: ignore[no-any-return]
    try:
        payload = await _web_json("news", base=settings.news_feed_base)
    except HTTPException as exc:
        raise HTTPException(status_code=502, detail=f"News feed unavailable: {exc.detail}")
    articles = await _normalize_espn_news(payload)
    return _store(
        "espn-news",
        {
            "source": "ESPN · NHL",
            "as_of": datetime.now(UTC).isoformat(),
            "articles": articles,
        },
    )  # type: ignore[return-value]


def _current_year_season_pair() -> tuple[int, int]:
    """(opening_year, season_start_year) for the season beginning now."""
    year = date.today().year if date.today().month >= 7 else date.today().year - 1
    return year, year - 1


def _roster_season_id() -> int:
    """NHL season id (e.g. 20262027) for the season starting now."""
    year, _ = _current_year_season_pair()
    return year * 10000 + (year + 1)


def _stats_season_id() -> int:
    """Season id of the most recent completed NHL season (e.g. 20252026)."""
    _, prev = _current_year_season_pair()
    return prev * 10000 + (prev + 1)


async def _fetch_season_rosters(season_id: int, db: AsyncSession) -> dict[int, dict]:
    """All 32 club rosters for a season, keyed by NHL player id (cached)."""
    settings = get_settings()
    key = f"nhl-rosters-{season_id}"
    cached = _cached(key, settings.roster_cache_ttl)
    if cached:
        return cached  # type: ignore[no-any-return]

    rows = (
        await db.execute(
            select(Team.abbreviation).where(
                Team.active == 1, Team.abbreviation != None  # noqa: E711
            )
        )
    ).scalars().all()
    abbrevs = [a for a in rows if a]

    # The database tags every historical identity as active, so take the 32
    # current clubs straight from the live standings feed instead.
    try:
        standings = await _web_json("standings/now")
        live = {
            (x.get("teamAbbrev") or {}).get("default")
            for x in standings.get("standings", [])
        }
        live = {a for a in live if a}
        if live:
            abbrevs = sorted(live)
    except (HTTPException, httpx.HTTPError):
        pass

    if not abbrevs:
        raise HTTPException(status_code=503, detail="Team list unavailable.")

    async def _one(abbr: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(
                f"{settings.nhl_web_api_base}/roster/{abbr}/{season_id}"
            )
            resp.raise_for_status()
            data = resp.json()
        persons = []
        for group in ("forwards", "defensemen", "goalies"):
            for p in data.get(group, []):
                first = p.get("firstName", {}).get("default", "") if isinstance(
                    p.get("firstName"), dict
                ) else p.get("firstName", "")
                last = p.get("lastName", {}).get("default", "") if isinstance(
                    p.get("lastName"), dict
                ) else p.get("lastName", "")
                pid = p.get("id")
                if pid:
                    persons.append(
                        {
                            "id": int(pid),
                            "name": f"{first} {last}".strip(),
                            "position": p.get("positionCode") or "",
                            "team": abbr,
                        }
                    )
        return persons

    results = await asyncio.gather(*(_one(a) for a in abbrevs), return_exceptions=True)
    roster: dict[int, dict] = {}
    for result in results:
        if isinstance(result, BaseException):
            continue
        for p in result:
            roster[p["id"]] = p
    if not roster:
        raise HTTPException(status_code=502, detail="Roster feed unavailable.")
    return _store(key, roster)  # type: ignore[return-value]


async def _player_landed_off(pids: list[int]) -> dict[int, bool]:
    """Which players the league reports as inactive (retired / no longer on an
    NHL roster), from the player-landing feed — cached per player and
    fault-tolerant. Only players reported NOT active are flagged; anything
    unresolved is left unflagged rather than mis-categorized."""
    landed_off: dict[int, bool] = {}

    async def one(pid: int) -> None:
        cache_key = f"player-landing-{pid}"
        cached = _cached(cache_key, get_settings().roster_cache_ttl)
        if cached is not None:
            if cached is True:
                landed_off[pid] = True
            return
        try:
            data = await _web_json(f"player/{pid}/landing")
        except (HTTPException, httpx.HTTPError):
            return
        flag = data.get("isActive") is False
        if flag:
            landed_off[pid] = True
        _store(cache_key, flag)

    await asyncio.gather(*(one(p) for p in pids))
    return landed_off


def _partition_retired(
    free: list[dict], landed_off: dict[int, bool]
) -> tuple[list[dict], list[dict]]:
    """Split a candidate list into active unsigned players vs. retired/off the
    roster per the league's own player-landing status."""
    free_agents: list[dict] = []
    retired: list[dict] = []
    for p in free:
        (retired if landed_off.get(p["player_id"]) else free_agents).append(p)
    return free_agents, retired


@router.get("/free-agents")
async def free_agents(
    limit: int = Query(60, ge=1, le=400),
    db: AsyncSession = Depends(get_db),
):
    """Players with 2025-26 NHL stats not on any 2026-27 club roster.

    Derived live: every club's official 2026-27 roster is fetched and unioned,
    then subtracted from the players who logged NHL games last season. Players
    left over are unsigned for the coming season — the free-agent watch.
    """
    stats_season = _stats_season_id()
    roster_season = _roster_season_id()
    roster = await _fetch_season_rosters(roster_season, db)

    rows = (
        await db.execute(
            select(
                PlayerSeasonStats.player_id,
                PlayerSeasonStats.team_abbrevs,
                PlayerSeasonStats.games_played,
                PlayerSeasonStats.goals,
                PlayerSeasonStats.assists,
                PlayerSeasonStats.points,
                PlayerSeasonStats.plus_minus,
            )
            .where(
                PlayerSeasonStats.season_id == stats_season,
                PlayerSeasonStats.game_type == 2,
                PlayerSeasonStats.games_played > 0,
            )
            .order_by(PlayerSeasonStats.points.desc())
        )
    ).all()

    pids = [r[0] for r in rows]
    players = (
        (await db.execute(select(Player).where(Player.id.in_(pids)))).scalars().all()
    )
    info = {
        p.id: {"name": p.full_name or p.last_name or str(p.id), "position": p.position_code, "birth": p.birth_date}
        for p in players
    }

    def _age(birth) -> int | None:
        if not birth:
            return None
        return max(int((datetime(2026, 9, 1) - birth).days / 365.25), 0)

    free: list[dict] = []
    for pid, _, gp, g, a, pts, pm in rows:
        if pid in roster:
            continue
        meta = info.get(pid) or {}
        free.append(
            {
                "player_id": pid,
                "name": meta.get("name") or str(pid),
                "position": meta.get("position"),
                "age": _age(meta.get("birth")),
                "games_played": gp,
                "goals": g,
                "assists": a,
                "points": pts,
                "plus_minus": pm,
            }
        )
        if len(free) >= min(limit * 2, 400):
            break

    landed_off = await _player_landed_off([p["player_id"] for p in free])
    free_agents, retired = _partition_retired(free, landed_off)

    return {
        "as_of": datetime.now(UTC).isoformat(),
        "stats_season": stats_season,
        "roster_season": roster_season,
        "count": len(free_agents),
        "free_agents": free_agents[:limit],
        "retired_count": len(retired),
        "retired": retired[:limit],
        "note": (
            "Players with NHL games last season who are not on any club's "
            "official roster for this season. Derived live from club rosters "
            "and the league's own player status."
        ),
    }


@router.get("/fantasy/pool")
async def fantasy_pool(
    stat_type: str = Query("skater", pattern="^(skater|goalie)$"),
    preset: str = Query("standard"),
    limit: int = Query(160, ge=1, le=400),
    game_type: int = Query(2, ge=2, le=3),
    db: AsyncSession = Depends(get_db),
):
    """Deterministic career fantasy pool for a scoring preset.

    Entertainment, for fun — computed from the same career totals the
    leaderboards use; never a claim about who is objectively best.
    """
    engine = StatisticsEngine(db)
    try:
        pool = await engine.get_fantasy_pool(
            preset=preset, stat_type=stat_type, limit=limit, game_type=game_type
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    presets = [
        {
            "key": k,
            "label": v["label"],
            "tagline": v["tagline"],
            "weights": v["weights"],
        }
        for k, v in FANTASY_PRESETS.items()
    ]
    return {**pool, "presets": presets}


def _team_digest(team_id: int | None, name: str | None, team_by_id: dict[int, Team]) -> dict | None:
    if team_id in team_by_id:
        t = team_by_id[team_id]
        return {
            "team_id": t.id,
            "name": t.full_name,
            "abbreviation": t.abbreviation,
            "logo": team_logo_url(t.abbreviation),
        }
    if name:
        return {"team_id": None, "name": name, "abbreviation": None, "logo": None}
    return None


@router.get("/champions")
async def champion_history(
    season_id: int | None = Query(None),
    team_id: int | None = Query(None, description="Filter by winner or finalist team/franchise"),
    limit: int = Query(200, ge=1, le=400),
    db: AsyncSession = Depends(get_db),
):
    """Championship history: Stanley Cup winners and finalists per season."""
    q = (
        select(Champion, Season.formatted_id)
        .join(Season, Season.id == Champion.season_id)
        .order_by(Season.id.desc())
    )
    if season_id is not None:
        q = q.where(Champion.season_id == season_id)
    rows = (await db.execute(q)).all()

    team_ids = {r[0].winner_team_id for r in rows} | {r[0].runner_team_id for r in rows}
    team_ids.discard(None)
    team_by_id: dict[int, Team] = {}
    if team_ids:
        team_q = await db.execute(select(Team).where(Team.id.in_(team_ids)))
        team_by_id = {t.id: t for t in team_q.scalars()}

    identity_ids: set[int] = set()
    if team_id is not None:
        franchise_id = None
        target = team_by_id.get(team_id)
        if target and target.franchise_id:
            franchise_id = target.franchise_id
        elif not target:
            target = await db.get(Team, team_id)
            franchise_id = target.franchise_id if target else None
        if franchise_id is not None:
            fid_q = await db.execute(select(Team.id).where(Team.franchise_id == franchise_id))
            identity_ids = set(fid_q.scalars())

    results = []
    for champion, label in rows:
        digest = {
            "season_id": champion.season_id,
            "season_label": label,
            "winner": _team_digest(champion.winner_team_id, champion.winner_name, team_by_id),
            "runner_up": _team_digest(champion.runner_team_id, champion.runner_name, team_by_id),
            "champ_wins": champion.champ_wins,
            "runner_wins": champion.runner_wins,
            "note": champion.note,
        }
        if identity_ids:
            involved = (champion.winner_team_id in identity_ids) or (
                champion.runner_team_id in identity_ids
            )
            if not involved:
                continue
            digest["won"] = champion.winner_team_id in identity_ids
        results.append(digest)
        if len(results) >= limit:
            break
    return {"count": len(results), "results": results}


@router.get("/playoffs/series")
async def playoff_series(
    season_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Restored playoff series (authoritative history).

    Conference finals come from the playoff_series table (16-team era,
    1993-94 through 2025-26); the Stanley Cup Final is merged from the
    champions table. Earlier rounds are noted as pending restoration.
    """
    q = (
        select(PlayoffSeries, Season.formatted_id)
        .join(Season, Season.id == PlayoffSeries.season_id)
        .order_by(PlayoffSeries.season_id.desc(), PlayoffSeries.conference)
    )
    if season_id is not None:
        q = q.where(PlayoffSeries.season_id == season_id)
    rows = (await db.execute(q)).all()

    cq = select(Champion, Season.formatted_id).join(Season, Season.id == Champion.season_id)
    if season_id is not None:
        cq = cq.where(Champion.season_id == season_id)
    champs = (await db.execute(cq.order_by(Season.id.desc()))).all()

    entries: list[dict] = []
    for series, label in rows:
        entries.append(
            {
                "season_id": series.season_id,
                "season_label": label,
                "round_number": series.round_number,
                "round_label": series.round_label,
                "conference": series.conference,
                "winner_team_id": series.winner_team_id,
                "winner_name": series.winner_name,
                "loser_team_id": series.loser_team_id,
                "loser_name": series.loser_name,
                "winner_games": series.winner_games,
                "loser_games": series.loser_games,
                "note": series.note,
            }
        )
    for champion, label in champs:
        entries.append(
            {
                "season_id": champion.season_id,
                "season_label": label or str(champion.season_id),
                "round_number": 4,
                "round_label": "Stanley Cup Final",
                "conference": None,
                "winner_team_id": champion.winner_team_id,
                "winner_name": champion.winner_name,
                "loser_team_id": champion.runner_team_id,
                "loser_name": champion.runner_name,
                "winner_games": champion.champ_wins,
                "loser_games": champion.runner_wins,
                "note": champion.note,
            }
        )

    team_ids = {e["winner_team_id"] for e in entries} | {e["loser_team_id"] for e in entries}
    team_ids.discard(None)
    team_by_id: dict[int, Team] = {}
    if team_ids:
        team_q = await db.execute(select(Team).where(Team.id.in_(team_ids)))
        team_by_id = {t.id: t for t in team_q.scalars()}

    results: list[dict] = []
    for e in entries:
        results.append(
            {
                "season_id": e["season_id"],
                "season_label": e["season_label"],
                "round_number": e["round_number"],
                "round_label": e["round_label"],
                "conference": e["conference"],
                "winner": _team_digest(e["winner_team_id"], e["winner_name"], team_by_id),
                "runner_up": _team_digest(e["loser_team_id"], e["loser_name"], team_by_id),
                "winner_games": e["winner_games"],
                "loser_games": e["loser_games"],
                "note": e["note"],
            }
        )
    results.sort(key=lambda r: (r["season_id"], r["round_number"], r["conference"] or ""))
    return {"count": len(results), "results": results}


@router.get("/standings")
async def standings(
    season_id: int = Query(20242025),
    game_type: int = Query(2, ge=2, le=3),
    split: str = Query("league", pattern="^(league|conference|division)$"),
    db: AsyncSession = Depends(get_db),
):
    """League standings computed from the database (team_season_stats).

    split=league collates all teams; split=conference|division groups by the
    current alignment (stable since 2013-14). Older seasons only have a league
    view, so the response falls back with a note.
    """
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
                "conference": team.conference,
                "division": team.division,
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

    all_split = all(r["conference"] for r in standings_rows)
    modern_alignment = season_id >= 20132014
    if split == "league" or not all_split or not modern_alignment:
        effective = "league"
        note = (
            "Conference and division splits apply from the 2013-14 alignment."
            if (not all_split or not modern_alignment)
            else "League-wide view sorted by points."
        )
        standings_rows.sort(
            key=lambda r: (r["points"], r["reg_wins"], r["goal_differential"]), reverse=True
        )
        for index, row in enumerate(standings_rows, start=1):
            row["rank"] = index
            row["in_playoffs"] = index <= 16
        return {
            "season_id": season_id,
            "season_label": rows[0][2],
            "game_type": game_type,
            "split": effective,
            "note": note,
            "rows": standings_rows,
        }

    group_key = "division" if split == "division" else "conference"
    group_label = "Division" if split == "division" else "Conference"
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for row in standings_rows:
        key = (row[group_key] or "Unknown")
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)
    for key in order:
        groups[key].sort(
            key=lambda r: (r["points"], r["reg_wins"], r["goal_differential"]), reverse=True
        )
        for index, row in enumerate(groups[key], start=1):
            row["rank"] = index
            row["in_playoffs"] = False
    playoff_ids = {
        r["team_id"]
        for r in sorted(
            standings_rows, key=lambda r: (r["points"], r["reg_wins"], r["goal_differential"]),
            reverse=True,
        )[:16]
    }
    for key in order:
        for row in groups[key]:
            row["in_playoffs"] = row["team_id"] in playoff_ids
    return {
        "season_id": season_id,
        "season_label": rows[0][2],
        "game_type": game_type,
        "split": split,
        "note": (
            f"Grouped by {group_label.lower()} (2013-14 alignment); "
            "playoff bubble = top 16 league-wide."
        ),
        "groups": [{"key": key, "label": key, "rows": groups[key]} for key in order],
    }
