"""Tests for the season-simulator service (entertainment, not betting)."""

import pytest

from app.models.player import Player
from app.models.stats import GoalieSeasonStats, PlayerSeasonStats
from app.models.stats_team import TeamSeasonStats
from app.models.team import Team
from app.services.statistics import simulation as sim

PRICE_RATE = sim._PRICE_PTS_WEIGHT + sim._PRICE_LAM_WEIGHT


async def _add_player(session, pid: int, name: str, position: str = "C") -> None:
    session.add(
        Player(
            id=pid,
            nhl_id=pid,
            full_name=name,
            first_name=name.split()[0],
            last_name=name.split()[-1],
            position_code=position,
            active=1,
            is_goalie=1 if position == "G" else 0,
        )
    )
    await session.flush()


async def _add_skater(session, pid: int, season: int, **kw) -> None:
    session.add(
        PlayerSeasonStats(
            player_id=pid,
            season_id=season,
            game_type=2,
            games_played=kw.get("games_played", 0),
            goals=kw.get("goals", 0),
            assists=kw.get("assists", 0),
            takeaways=kw.get("takeaways"),
            team_abbrevs=kw.get("team_abbrevs", "EDM"),
        )
    )
    await session.flush()


async def _add_goalie(session, pid: int, season: int, **kw) -> None:
    session.add(
        GoalieSeasonStats(
            player_id=pid,
            season_id=season,
            game_type=2,
            games_played=kw.get("games_played", 0),
            wins=kw.get("wins", 0),
            shutouts=kw.get("shutouts", 0),
            goals_against=kw.get("goals_against", 0),
            team_abbrevs=kw.get("team_abbrevs", "EDM"),
        )
    )
    await session.flush()


async def _add_team(session, tid: int, season: int, name: str, abbr: str) -> None:
    session.add(Team(id=tid, name=f"{name}", full_name=name, abbreviation=abbr))
    session.add(
        TeamSeasonStats(
            team_id=tid,
            season_id=season,
            game_type=2,
            games_played=82,
            wins=41,
            losses=30,
            ot_losses=11,
            points=93,
            goals_for=250,
            goals_against=220,
        )
    )
    await session.flush()


def test_poisson_zero_probability():
    assert sim.poisson_p0(0.0) == 1.0
    assert sim.poisson_p0(3.0) == pytest.approx(0.0498, rel=1e-2)
    assert 0 < sim.poisson_p0(1.0) < 1


def test_p_at_least_bounds_and_monotonic():
    assert sim.p_at_least(0.0) == 0.0
    for lam in (0.05, 0.5, 1.0, 2.5):
        p = sim.p_at_least(lam)
        assert 0 <= p <= 1
    assert sim.p_at_least(0.3) < sim.p_at_least(0.9)


def test_player_probs_shape_and_range():
    probs = sim.player_probs(40, 50, 60, 82)
    assert set(probs) == {"points", "goals", "assists", "takeaways"}
    for v in probs.values():
        assert 0 <= v <= 1
    # P(≥1 point) >= P(≥1 goal)
    assert probs["points"] >= probs["goals"]
    # zero games -> all zeros
    empty = sim.player_probs(10, 10, 10, 0)
    assert empty["goals"] == 0.0


def test_pythag_balance_and_extremes():
    assert sim._pythag(0, 0) == 0.5
    assert sim._pythag(2, 3) < 0.5
    assert sim._pythag(3, 2) > 0.5
    assert 0 < sim._pythag(200, 150) < 1


def test_sample_is_seeded_and_stable():
    a = [sim._sample(1.7, __import__("random").Random(42)) for _ in range(20)]
    b = [sim._sample(1.7, __import__("random").Random(42)) for _ in range(20)]
    assert a == b
    assert all(x >= 0 for x in a)


async def test_build_shop_prices_and_probs(session):
    await _add_team(session, 1, 20242025, "Edmonton Oilers", "EDM")
    await _add_player(session, 10, "Test Forward", "C")
    await _add_skater(
        session, 10, 20242025, games_played=82, goals=40, assists=50, takeaways=60
    )
    await _add_player(session, 20, "Test Goalie", "G")
    await _add_goalie(
        session, 20, 20242025, games_played=60, wins=40, shutouts=8, goals_against=140,
    )

    shop = await sim.build_shop(session, 20242025)

    assert shop["budget"] == sim.BUDGET
    assert shop["season"] == 20242025
    assert shop["games_per_team"] == sim.GAMES_PER_TEAM
    assert "note" in shop

    assert len(shop["teams"]) == 1
    t = shop["teams"][0]
    assert t["team_id"] == 1
    assert t["probs"]["win"] == pytest.approx(41 / 82, rel=1e-4)
    assert t["price"] >= 12
    assert t["price"] == max(12, round(41 / 82 * sim._TEAM_WIN_PRICE))

    sk = {p["player_id"]: p for p in shop["skaters"]}
    assert 10 in sk
    s = sk[10]
    assert s["price"] >= 1
    # ~90 pts over 82 games -> lam ~1.1/game; P(≥1) < 1, price positive
    assert s["probs"]["points"] > s["probs"]["goals"]
    assert s["price"] <= round(PRICE_RATE) + 100

    g = {p["player_id"]: p for p in shop["goalies"]}
    assert 20 in g
    assert g[20]["probs"]["shutout"] == round(
        sim.poisson_p0(140 / 60), 4
    )
    assert g[20]["price"] >= 2


async def test_run_season_full_round_robin(session):
    await _add_team(session, 1, 20242025, "Team One", "ONE")
    await _add_team(session, 2, 20242025, "Team Two", "TWO")
    await _add_player(session, 10, "Forward One", "C")
    await _add_skater(
        session, 10, 20242025, games_played=82, goals=40, assists=50, takeaways=60,
        team_abbrevs="ONE",
    )
    await _add_player(session, 20, "Goalie One", "G")
    await _add_goalie(
        session, 20, 20242025, games_played=60, wins=40, shutouts=8, goals_against=140,
        team_abbrevs="ONE",
    )

    result = await sim.run_season(session, 20242025, [10], [20], [1], seed=7)

    assert result["season"] == 20242025
    assert result["games_per_team"] == sim.GAMES_PER_TEAM
    # two clubs -> 2 games each in the double round robin
    assert len(result["standings"]) == 2
    for r in result["standings"]:
        assert r["gp"] == 2
        assert r["w"] + r["l"] + r["otl"] == 2
        assert r["pts"] == 2 * r["w"] + r["otl"]
    # ranking always populated, in descending pts order
    pts = [r["pts"] for r in result["standings"]]
    assert pts == sorted(pts, reverse=True)
    owned = [r for r in result["standings"] if r["owned"]]
    assert len(owned) == 1 and owned[0]["team_id"] == 1

    assert len(result["stable"]) == 1
    stable = result["stable"][0]
    assert stable["player_id"] == 10
    assert stable["gp"] == sim.GAMES_PER_TEAM
    assert stable["points"] == stable["goals"] + stable["assists"]
    assert 0 <= stable["takeaways"]

    assert len(result["crease"]) == 1
    c = result["crease"][0]
    assert c["player_id"] == 20
    assert c["wins"] <= c["gp"]

    p = result["portfolio"]
    assert p["budget"] == sim.BUDGET
    assert p["spent"] > 0
    assert p["balance"] == round(p["budget"] - p["spent"], 2)
    assert round(p["value"] - p["balance"], 2) == round(p["gain"] + p["spent"], 2)


async def test_run_season_deterministic_with_seed(session):
    await _add_team(session, 1, 20242025, "Team One", "ONE")
    await _add_team(session, 2, 20242025, "Team Two", "TWO")

    r1 = await sim.run_season(session, 20242025, [], [], [1, 2], seed=1)
    r2 = await sim.run_season(session, 20242025, [], [], [1, 2], seed=1)
    assert r1["standings"] == r2["standings"]
    assert r1["portfolio"] == r2["portfolio"]


async def test_run_season_empty_picks_still_plays(session):
    await _add_team(session, 1, 20242025, "Team One", "ONE")
    await _add_team(session, 2, 20242025, "Team Two", "TWO")

    result = await sim.run_season(session, 20242025, [], [], [], seed=3)
    assert len(result["standings"]) == 2
    assert result["stable"] == []
    assert result["crease"] == []
    assert result["portfolio"]["spent"] == 0