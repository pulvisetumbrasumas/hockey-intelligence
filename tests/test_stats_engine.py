"""Tests for the deterministic statistics engine."""

from app.models.player import Player
from app.models.stats import GoalieSeasonStats, PlayerSeasonStats
from app.services.statistics.engine import StatisticsEngine


async def _add_player(session, pid: int, name: str, position: str = "C") -> Player:
    p = Player(
        id=pid,
        nhl_id=pid,
        full_name=name,
        first_name=name.split()[0],
        last_name=name.split()[-1],
        position_code=position,
        active=1,
        is_goalie=1 if position == "G" else 0,
    )
    session.add(p)
    await session.flush()
    return p


async def _add_skater(session, pid: int, season: int, game_type: int = 2, **kw) -> None:
    session.add(
        PlayerSeasonStats(
            player_id=pid,
            season_id=season,
            game_type=game_type,
            games_played=kw.get("games_played", 0),
            goals=kw.get("goals", 0),
            assists=kw.get("assists", 0),
            plus_minus=kw.get("plus_minus", 0),
            penalty_minutes=kw.get("penalty_minutes", 0),
            pp_goals=kw.get("pp_goals", 0),
            sh_goals=kw.get("sh_goals", 0),
            game_winning_goals=kw.get("game_winning_goals", 0),
            ot_goals=kw.get("ot_goals", 0),
            shots=kw.get("shots", 0),
        )
    )
    await session.flush()


async def _add_goalie(session, pid: int, season: int, game_type: int = 2, **kw) -> None:
    session.add(
        GoalieSeasonStats(
            player_id=pid,
            season_id=season,
            game_type=game_type,
            games_played=kw.get("games_played", 0),
            games_started=kw.get("games_started", 0),
            wins=kw.get("wins", 0),
            losses=kw.get("losses", 0),
            ot_losses=kw.get("ot_losses", 0),
            shutouts=kw.get("shutouts", 0),
            goals_against=kw.get("goals_against", 0),
            shots_against=kw.get("shots_against", 0),
            saves=kw.get("saves", 0),
            time_on_ice=kw.get("time_on_ice", 0),
        )
    )
    await session.flush()


async def test_career_skater_aggregates_regular_and_playoff(session):
    await _add_player(session, 1, "Test Player")
    await _add_skater(session, 1, 20222023, games_played=30, goals=10, assists=20)
    await _add_skater(session, 1, 20232024, games_played=40, goals=15, assists=25)
    await _add_skater(session, 1, 20232024, 3, games_played=10, goals=3, assists=5)

    result = await StatisticsEngine(session).get_player_career_stats(1)

    reg = result["regular_season"]
    assert reg["games_played"] == 70
    assert reg["goals"] == 25
    assert reg["assists"] == 45
    assert reg["points"] == 70
    assert reg["points_per_game"] == 1.0
    assert reg["seasons_played"] == 2

    po = result["playoffs"]
    assert po["games_played"] == 10
    assert po["goals"] == 3
    assert po["points"] == 8


async def test_career_skater_ppg_zero_games_is_none(session):
    await _add_player(session, 1, "Test Player")
    await _add_skater(session, 1, 20222023)

    reg = (await StatisticsEngine(session).get_player_career_stats(1))["regular_season"]
    assert reg["points_per_game"] is None
    assert reg["seasons_played"] == 0


async def test_career_goalie_aggregation(session):
    await _add_player(session, 2, "Test Goalie", position="G")
    await _add_goalie(
        session, 2, 20222023, games_played=50, games_started=50,
        wins=30, losses=15, ot_losses=5, shutouts=6,
        shots_against=1350, saves=1250, goals_against=100, time_on_ice=3000,
    )

    result = await StatisticsEngine(session).get_player_career_stats(2)
    reg = result["regular_season_goalie"]
    assert reg["wins"] == 30
    assert reg["shutouts"] == 6
    assert round(reg["save_pct"], 4) == round(1250 / 1350, 4)
    assert reg["seasons_played"] == 1


async def test_career_unknown_player_is_empty(session):
    result = await StatisticsEngine(session).get_player_career_stats(999)
    assert result["regular_season"] == {}
    assert result["playoffs"] == {}
    assert result["regular_season_goalie"] == {}
    assert result["playoffs_goalie"] == {}


async def test_season_stats_returns_skater_and_goalie(session):
    await _add_player(session, 1, "Test Player")
    await _add_player(session, 2, "Test Goalie", position="G")
    await _add_skater(session, 1, 20222023, games_played=70, goals=20, assists=30)
    await _add_goalie(session, 2, 20222023, games_played=50, wins=25)

    result = await StatisticsEngine(session).get_player_season_stats(1, 20222023)
    assert result is not None
    assert result["skater"] is not None
    assert result["skater"]["games_played"] == 70
    assert result["goalie"] is None

    result = await StatisticsEngine(session).get_player_season_stats(2, 20222023)
    assert result is not None
    assert result["skater"] is None
    assert result["goalie"] is not None
    assert result["goalie"]["wins"] == 25


async def test_season_stats_missing_returns_none(session):
    result = await StatisticsEngine(session).get_player_season_stats(1, 20222023)
    assert result is None


async def test_weighted_avg(session):
    engine = StatisticsEngine(session)
    assert engine._weighted_avg([0.9, 0.95], [100, 100]) == 0.925
    assert engine._weighted_avg([], []) is None
    assert engine._weighted_avg([0.9], [0]) == 0.9


async def test_compare_players_never_declares_single_winner(session):
    await _add_player(session, 1, "Alpha Player")
    await _add_player(session, 2, "Beta Player")
    await _add_skater(session, 1, 20222023, games_played=82, goals=40, assists=40, pp_goals=10)
    await _add_skater(session, 2, 20222023, games_played=82, goals=25, assists=30, pp_goals=5)

    result = await StatisticsEngine(session).compare_players([1, 2])

    assert "winner" not in result
    names = [p["name"] for p in result["players"]]
    assert names == ["Alpha Player", "Beta Player"]
    assert "offense" in result["evidence"]
    values = result["evidence"]["offense"]["values"]["points"]
    assert values.get(1) == 80
    assert values.get(2) == 55
    assert "notes" in result


async def test_compare_players_dimensions_param(session):
    await _add_player(session, 1, "Alpha Player")
    await _add_player(session, 2, "Beta Player")
    await _add_skater(session, 1, 20222023, games_played=82, goals=40, assists=40)
    await _add_skater(session, 2, 20222023, games_played=82, goals=25, assists=30)

    result = await StatisticsEngine(session).compare_players([1, 2], ["durability"])
    assert result["dimensions"] == ["durability"]
    assert list(result["evidence"].keys()) == ["durability"]

    result_all = await StatisticsEngine(session).compare_players(
        [1, 2], ["durability", "efficiency"]
    )
    assert list(result_all["evidence"].keys()) == ["durability", "efficiency"]


async def test_thread_id_zero_skaters_only(session):
    """A zero-GP placeholder row must not count as a played season."""
    await _add_player(session, 1, "Test Player")
    await _add_skater(session, 1, 20222023, games_played=0)
    reg = (await StatisticsEngine(session).get_player_career_stats(1))["regular_season"]
    assert reg["seasons_played"] == 0
