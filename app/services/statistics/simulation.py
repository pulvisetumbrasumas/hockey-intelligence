"""Season simulator — entertainment, not betting.

A deterministic buy-then-play loop: players and teams carry probability-style
"chances" (points, goals, assists, takeaways; shutouts; team win) computed from
real league rates, priced in an arbitrary simulation budget. Buying adds their
output to the league; the simulator then plays a compressed 62-game regular
season and returns standings plus the purchased stable's simulated totals.

None of this is a prediction or a claim about objective truth — it is a toy
that reuses the same database the leaderboards use.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Player, PlayerSeasonStats, Team, TeamSeasonStats
from app.models.stats import GoalieSeasonStats

GAMES_PER_TEAM = 62  # double round robin, home and away vs every other club
BUDGET = 100
POIS_EXPONENT = 2.35  # Pythagorean-style win expectation
RESELL_RATE = 0.8
_MIN_SHOP_GP = 20  # ignore one-off/partial rows so prices use real sample sizes

_PRICE_PTS_WEIGHT = 16.0  # credits vs P(≥1 point) on a single game
_PRICE_LAM_WEIGHT = 5.0  # credits vs expected points/game
_GOALIE_SO_PRICE = 40.0  # credits vs P(shutout) on a single game
_GOALIE_WIN_PRICE = 20.0  # credits vs win rate
_TEAM_WIN_PRICE = 70.0  # credits at a .500 club, scales linearly

_VALUE_POINT = 0.35  # credits per simulated point
_VALUE_WIN = 1.2
_VALUE_SHUTOUT = 2.5
_VALUE_TEAM_WIN = 0.8
_VALUE_TEAM_OTL = 0.4

_GOAL_BOOST = 0.05  # goals/game contributed per owned skater (times their rate)
_GOAL_BOOST_CAP = 0.45
_GA_CUT = 0.96  # multiplier on goals against per owned goalie
_GA_CUT_FLOOR = 0.85
_FRANCHISE_BOOST = 0.06  # goals/game for an owned franchise
_FRANCHISE_BOOST_CAP = 0.5

_PSS_PLAYER_COLS = (
    PlayerSeasonStats.player_id,
    PlayerSeasonStats.games_played,
    PlayerSeasonStats.goals,
    PlayerSeasonStats.assists,
    PlayerSeasonStats.takeaways,
    PlayerSeasonStats.team_abbrevs,
    PlayerSeasonStats.wins,
    PlayerSeasonStats.shutouts,
    PlayerSeasonStats.goals_against,
    PlayerSeasonStats.is_goalie,
    PlayerSeasonStats.season_id,
    PlayerSeasonStats.game_type,
)


_GS_STATS_COLS = (
    GoalieSeasonStats.player_id,
    GoalieSeasonStats.games_played,
    GoalieSeasonStats.wins,
    GoalieSeasonStats.shutouts,
    GoalieSeasonStats.goals_against,
    GoalieSeasonStats.team_abbrevs,
    GoalieSeasonStats.season_id,
    GoalieSeasonStats.game_type,
)


def poisson_p0(lam: float) -> float:
    """P(X = 0) for a Poisson occurrence rate lambda (per single game)."""
    return math.exp(-lam) if lam > 0 else 1.0


def p_at_least(lam: float) -> float:
    """P(X ≥ 1) for a game-level Poisson rate."""
    return 1.0 - poisson_p0(lam)


def _sample(lam: float, rng: random.Random) -> int:
    if lam <= 0:
        return 0
    limit = math.exp(-lam)
    k, prob = 0, 1.0
    while True:
        prob *= rng.random()
        if prob <= limit:
            return k
        k += 1


def _rate(num: int | None, gp: int | None) -> float:
    if not gp:
        return 0.0
    return max(float(num or 0) / gp, 0.0)


def player_probs(
    goals: int | None, assists: int | None, takeaways: int | None, gp: int | None
) -> dict[str, float]:
    return {
        "points": round(p_at_least(_rate(goals, gp) + _rate(assists, gp)), 4),
        "goals": round(p_at_least(_rate(goals, gp)), 4),
        "assists": round(p_at_least(_rate(assists, gp)), 4),
        "takeaways": round(p_at_least(_rate(takeaways, gp)), 4),
    }


def _pythag(gf: float, ga: float) -> float:
    if gf + ga <= 0:
        return 0.5
    return gf**POIS_EXPONENT / (gf**POIS_EXPONENT + ga**POIS_EXPONENT)


async def _pss_rows(
    db: AsyncSession, season_id: int, player_ids: list[int] | None = None
) -> list[Any]:
    cols = _PSS_PLAYER_COLS
    q = select(*cols).where(
        PlayerSeasonStats.season_id == season_id,
        PlayerSeasonStats.game_type == 2,
    )
    if player_ids:
        q = q.where(PlayerSeasonStats.player_id.in_([int(x) for x in player_ids]))
    return list((await db.execute(q)).all())


async def _gs_rows(
    db: AsyncSession, season_id: int, player_ids: list[int] | None = None
) -> list[Any]:
    cols = _GS_STATS_COLS
    q = select(*cols).where(
        GoalieSeasonStats.season_id == season_id,
        GoalieSeasonStats.game_type == 2,
    )
    if player_ids:
        q = q.where(GoalieSeasonStats.player_id.in_([int(x) for x in player_ids]))
    return list((await db.execute(q)).all())


async def _load_teams(
    db: AsyncSession, season_id: int
) -> tuple[
    dict[int, tuple[float, float, float, float]], dict[int, Team], dict[str, int]
]:
    rows = (
        await db.execute(
            select(
                TeamSeasonStats.team_id,
                TeamSeasonStats.games_played,
                TeamSeasonStats.wins,
                TeamSeasonStats.goals_for,
                TeamSeasonStats.goals_against,
            ).where(
                TeamSeasonStats.season_id == season_id,
                TeamSeasonStats.game_type == 2,
                TeamSeasonStats.games_played > 0,
            )
        )
    ).all()
    team_ids = {int(r[0]) for r in rows}
    teams = (
        (await db.execute(select(Team).where(Team.id.in_(team_ids)))).scalars().all()
    )
    team_info = {int(t.id): t for t in teams}
    base: dict[int, tuple[float, float, float, float]] = {}
    abbr_to_team: dict[str, int] = {}
    for r in rows:
        tid = int(r[0])
        gp = int(r[1] or 0)
        wins = int(r[2] or 0)
        gf = _rate(r[3], gp)
        ga = _rate(r[4], gp)
        base[tid] = (gf, ga, wins / gp if gp else 0.0, float(gp))
        team = team_info.get(tid)
        if team is not None and team.abbreviation:
            abbr_to_team[team.abbreviation] = tid
    return base, team_info, abbr_to_team


async def build_shop(db: AsyncSession, season_id: int) -> dict:
    rows = await _pss_rows(db, season_id)
    goalie_rows = await _gs_rows(db, season_id)
    pids = [int(r[0]) for r in rows] + [int(r[0]) for r in goalie_rows]
    players = (
        (await db.execute(select(Player).where(Player.id.in_(pids)))).scalars().all()
    )
    player_info = {int(p.id): p for p in players}

    base, team_info, _ = await _load_teams(db, season_id)

    skaters: list[dict] = []
    for (
        pid_raw,
        gp_raw,
        goals_raw,
        assists_raw,
        tk_raw,
        abbr_raw,
        _wins_raw,
        _so_raw,
        _ga_raw,
        _is_goalie_raw,
        _,
        _,
    ) in rows:
        pid = int(pid_raw)
        p = player_info.get(pid)
        if p is None:
            continue
        gp = int(gp_raw or 0)
        if gp < _MIN_SHOP_GP:
            continue
        position = p.position_code or ""
        if position == "G" or bool(_is_goalie_raw):
            continue
        goals = int(goals_raw or 0)
        assists = int(assists_raw or 0)
        tk = int(tk_raw or 0)
        lam_pts = _rate(goals, gp) + _rate(assists, gp)
        skaters.append(
            {
                "player_id": pid,
                "name": p.full_name or p.last_name or str(pid),
                "team": str(abbr_raw or ""),
                "position": position,
                "games_played": gp,
                "goals": goals,
                "assists": assists,
                "points": goals + assists,
                "takeaways": tk,
                "probs": player_probs(goals, assists, tk, gp),
                "price": max(
                    1.0,
                    round(
                        p_at_least(lam_pts) * _PRICE_PTS_WEIGHT
                        + lam_pts * _PRICE_LAM_WEIGHT
                    ),
                ),
            }
        )

    goalies: list[dict] = []
    for (
        pid_raw,
        gp_raw,
        wins_raw,
        so_raw,
        ga_raw,
        abbr_raw,
        _,
        _,
    ) in goalie_rows:
        pid = int(pid_raw)
        p = player_info.get(pid)
        if p is None:
            continue
        gp = int(gp_raw or 0)
        if gp < _MIN_SHOP_GP:
            continue
        position = p.position_code or ""
        wins = int(wins_raw or 0)
        ga = int(ga_raw or 0)
        so = int(so_raw or 0)
        p_so = poisson_p0(_rate(ga, gp))
        p_win = wins / gp
        goalies.append(
            {
                "player_id": pid,
                "name": p.full_name or p.last_name or str(pid),
                "team": str(abbr_raw or ""),
                "position": position,
                "games_played": gp,
                "wins": wins,
                "shutouts": so,
                "goals_against": ga,
                "probs": {"shutout": round(p_so, 4), "win": round(p_win, 4)},
                "price": max(
                    2.0, round(p_so * _GOALIE_SO_PRICE + p_win * _GOALIE_WIN_PRICE)
                ),
            }
        )

    teams_out: list[dict] = []
    for tid, (gf, ga, win_pct, gp) in base.items():
        team = team_info.get(tid)
        if team is None:
            continue
        teams_out.append(
            {
                "team_id": tid,
                "name": team.full_name,
                "abbreviation": team.abbreviation,
                "win_pct": round(win_pct, 4),
                "gf_per_game": round(gf, 3),
                "ga_per_game": round(ga, 3),
                "probs": {"win": round(win_pct, 4)},
                "price": max(12.0, round(win_pct * _TEAM_WIN_PRICE)),
            }
        )

    skaters.sort(key=lambda x: -x["price"])
    goalies.sort(key=lambda x: -x["price"])
    return {
        "season": season_id,
        "games_per_team": GAMES_PER_TEAM,
        "budget": BUDGET,
        "skaters": skaters[:150],
        "goalies": goalies,
        "teams": sorted(teams_out, key=lambda x: -x["price"]),
        "note": (
            "Chances are game-level Poisson estimates from last season's rates; "
            "prices are made-up credits for a toy season. Not betting advice, "
            "not a prediction — just the same database, played."
        ),
    }


async def run_season(
    db: AsyncSession,
    season_id: int,
    skater_ids: list[int],
    goalie_ids: list[int],
    team_ids: list[int],
    seed: int | None = None,
) -> dict:
    rng = random.Random(seed)
    base, team_info, abbr_to_team = await _load_teams(db, season_id)
    team_rows = {tid: list(v) for tid, v in base.items()}

    owned_teams = {int(x) for x in team_ids} & set(team_rows)
    for tid in owned_teams:
        team_rows[tid][0] = min(
            team_rows[tid][0] + _FRANCHISE_BOOST,
            team_rows[tid][0] + _FRANCHISE_BOOST_CAP,
        )

    skaters: dict[int, dict[str, Any]] = {}
    if skater_ids:
        rows = await _pss_rows(db, season_id, skater_ids)
        players = (
            (
                await db.execute(
                    select(Player).where(Player.id.in_([int(x) for x in skater_ids]))
                )
            )
            .scalars()
            .all()
        )
        p_info = {int(p.id): p for p in players}
        for (
            pid_raw,
            gp_raw,
            goals_raw,
            assists_raw,
            tk_raw,
            abbr_raw,
            _,
            _,
            _,
            _,
            _,
            _,
        ) in rows:
            pid = int(pid_raw)
            abbr = str(abbr_raw or "")
            team_id = abbr_to_team.get(abbr)
            if team_id is None or team_id not in team_rows:
                continue
            p = p_info.get(pid)
            gp = int(gp_raw or 0)
            goals = int(goals_raw or 0)
            assists = int(assists_raw or 0)
            tk = int(tk_raw or 0)
            skaters[pid] = {
                "name": p.full_name or p.last_name or str(pid) if p else str(pid),
                "position": (p.position_code or "") if p else "",
                "team": team_id,
                "team_abbr": abbr,
                "gp": gp,
                "lg_goals": goals,
                "lg_assists": assists,
                "lg_tk": tk,
            }
            team_rows[team_id][0] += min(_GOAL_BOOST * _rate(goals, gp), _GOAL_BOOST_CAP)

    crease_meta: dict[int, dict[str, Any]] = {}
    if goalie_ids:
        rows = await _gs_rows(db, season_id, goalie_ids)
        players = (
            (
                await db.execute(
                    select(Player).where(Player.id.in_([int(x) for x in goalie_ids]))
                )
            )
            .scalars()
            .all()
        )
        p_info = {int(p.id): p for p in players}
        for (
            pid_raw,
            gp_raw,
            wins_raw,
            so_raw,
            ga_raw,
            abbr_raw,
            _,
            _,
        ) in rows:
            pid = int(pid_raw)
            abbr = str(abbr_raw or "")
            team_id = abbr_to_team.get(abbr)
            if team_id is None or team_id not in team_rows:
                continue
            p = p_info.get(pid)
            crease_meta[pid] = {
                "name": p.full_name or p.last_name or str(pid) if p else str(pid),
                "team": team_id,
                "team_abbr": abbr,
                "gp": int(gp_raw or 0),
                "lg_so": int(so_raw or 0),
                "lg_ga": int(ga_raw or 0),
                "lg_wins": int(wins_raw or 0),
            }
            team_rows[team_id][1] = max(
                team_rows[team_id][1] * _GA_CUT, _GA_CUT_FLOOR
            )

    # -- play the compressed double round robin --
    tids = sorted(team_rows)
    standings: dict[int, dict[str, int]] = {
        tid: {"w": 0, "l": 0, "otl": 0, "pts": 0, "gf": 0, "ga": 0, "gp": 0}
        for tid in tids
    }
    for i in tids:
        for j in tids:
            if i >= j:
                continue
            for home, away in ((i, j), (j, i)):
                gf_h = _sample(team_rows[home][0], rng)
                ga_h = _sample(team_rows[away][0], rng)
                h, a = standings[home], standings[away]
                h["gp"] += 1
                a["gp"] += 1
                h["gf"] += gf_h
                h["ga"] += ga_h
                a["gf"] += ga_h
                a["ga"] += gf_h
                if gf_h != ga_h:
                    h["w"] += 1
                    a["l"] += 1
                    h["pts"] += 2
                else:
                    ph = _pythag(team_rows[home][0], team_rows[home][1])
                    if rng.random() < ph:
                        h["w"] += 1
                        a["otl"] += 1
                        h["pts"] += 2
                        a["pts"] += 1
                    else:
                        a["w"] += 1
                        h["otl"] += 1
                        a["pts"] += 2
                        h["pts"] += 1

    rows = []
    for tid in tids:
        r = standings[tid]
        team = team_info.get(tid)
        if team is None:
            continue
        rows.append(
            {
                "team_id": tid,
                "name": team.full_name,
                "abbreviation": team.abbreviation,
                "owned": tid in owned_teams,
                "gp": r["gp"],
                "w": r["w"],
                "l": r["l"],
                "otl": r["otl"],
                "pts": r["pts"],
                "gf": r["gf"],
                "ga": r["ga"],
                "diff": r["gf"] - r["ga"],
            }
        )
    rows.sort(key=lambda r: (-r["pts"], -r["diff"]))
    for rank, r in enumerate(rows, start=1):
        r["rank"] = rank
        r["playoff"] = rank <= 8

    value = 0.0
    stable: list[dict] = []
    for pid, meta in skaters.items():
        used = min(GAMES_PER_TEAM, max(1, round(meta["gp"] * GAMES_PER_TEAM / 82)))
        g = _sample(_rate(meta["lg_goals"], meta["gp"]) * used, rng)
        a = _sample(_rate(meta["lg_assists"], meta["gp"]) * used, rng)
        tk = _sample(_rate(meta["lg_tk"], meta["gp"]) * used, rng)
        pts = g + a
        value += pts * _VALUE_POINT
        stable.append(
            {
                "player_id": pid,
                "name": meta["name"],
                "position": meta["position"],
                "team": meta["team_abbr"],
                "gp": used,
                "goals": g,
                "assists": a,
                "points": pts,
                "takeaways": tk,
            }
        )
    stable.sort(key=lambda x: -x["points"])

    crease: list[dict] = []
    for pid, meta in crease_meta.items():
        used = min(GAMES_PER_TEAM, max(1, round(meta["gp"] * GAMES_PER_TEAM / 82)))
        pwin = _pythag(team_rows[meta["team"]][0], team_rows[meta["team"]][1])
        wins = min(used, round(used * pwin))
        so = _sample(_rate(meta["lg_so"], meta["gp"]) * used, rng)
        ga = round(_rate(meta["lg_ga"], meta["gp"]) * used)
        value += wins * _VALUE_WIN + so * _VALUE_SHUTOUT
        crease.append(
            {
                "player_id": pid,
                "name": meta["name"],
                "team": meta["team_abbr"],
                "gp": used,
                "wins": wins,
                "shutouts": so,
                "goals_against": ga,
            }
        )
    crease.sort(key=lambda x: -x["wins"])

    for r in rows:
        if r["owned"]:
            value += r["w"] * _VALUE_TEAM_WIN + r["otl"] * _VALUE_TEAM_OTL

    spent = await _spent_for(db, season_id, skater_ids, goalie_ids, team_ids)
    return {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "season": season_id,
        "games_per_team": GAMES_PER_TEAM,
        "standings": rows,
        "stable": stable,
        "crease": crease,
        "portfolio": {
            "budget": BUDGET,
            "spent": spent,
            "balance": round(BUDGET - spent, 2),
            "value": round(value + (BUDGET - spent), 2),
            "gain": round(value - spent, 2),
        },
        "note": (
            "Simulated entertainment — every result sampled from last season's "
            "rates with owned players added to their club's offense and owned "
            "goalies shaving goals against. Not a prediction."
        ),
    }


async def _spent_for(db, season_id, skater_ids, goalie_ids, team_ids) -> float:
    shop = await build_shop(db, season_id)
    by_id = {p["player_id"]: p["price"] for p in shop["skaters"] + shop["goalies"]}
    by_team = {t["team_id"]: t["price"] for t in shop["teams"]}
    total = sum(by_id.get(int(x), 0.0) for x in skater_ids)
    total += sum(by_id.get(int(x), 0.0) for x in goalie_ids)
    total += sum(by_team.get(int(x), 0.0) for x in team_ids)
    return round(total, 2)