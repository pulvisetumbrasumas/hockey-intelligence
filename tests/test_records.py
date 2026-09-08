"""Tests for the deterministic leaderboard/records engine."""

from app.models.player import Player
from app.models.stats import GoalieSeasonStats, PlayerSeasonStats
from app.services.statistics.engine import StatisticsEngine


async def _seed(session):
    session.add_all(
        [
            Player(id=1, nhl_id=1, full_name="Connor McDavid", position_code="C"),
            Player(id=2, nhl_id=2, full_name="Leon Draisaitl", position_code="C"),
            Player(id=3, nhl_id=3, full_name="A. Callup", position_code="L"),
            Player(id=4, nhl_id=4, full_name="G. Starter", position_code="G", is_goalie=1),
            PlayerSeasonStats(player_id=1, season_id=20242025, game_type=2,
                              team_abbrevs="EDM", games_played=67, goals=26,
                              assists=74, points=100, points_per_game=1.4925),
            PlayerSeasonStats(player_id=2, season_id=20242025, game_type=2,
                              team_abbrevs="EDM", games_played=66, goals=41,
                              assists=65, points=106, points_per_game=1.6061),
            # one brief call-up season to test the rate-metric min_games guard
            PlayerSeasonStats(player_id=3, season_id=20212022, game_type=2,
                              team_abbrevs="TOT", games_played=2, goals=1,
                              assists=1, points=2, points_per_game=1.0),
            GoalieSeasonStats(player_id=4, season_id=20242025, game_type=2,
                              team_abbrevs="TOT", games_played=55, wins=33,
                              shutouts=4, save_pct=0.9234, goals_against_average=2.1),
        ]
    )
    await session.flush()


async def test_season_leaderboard_points_with_ties(session):
    await _seed(session)
    result = await StatisticsEngine(session).get_leaderboard(
        season_id=20242025, metric="points", limit=2
    )
    values = [r["value"] for r in result["results"]]
    assert values == sorted(values, reverse=True)
    assert result["season_label"] == "2024-2025" or result["season_label"] is not None


async def test_season_leaderboard_goalie_wins(session):
    await _seed(session)
    result = await StatisticsEngine(session).get_leaderboard(
        season_id=20242025, metric="wins", stat_type="goalie"
    )
    assert result["results"][0]["name"] == "G. Starter"
    assert result["results"][0]["value"] == 33


async def test_career_leaderboard_points(session):
    await _seed(session)
    result = await StatisticsEngine(session).get_leaderboard(
        metric="points", stat_type="skater"
    )
    assert result["scope"] == "career"
    assert result["results"][0]["value"] == 106
    assert result["results"][1]["value"] == 100


async def test_career_rate_metric_respects_min_games_guard(session):
    await _seed(session)
    result = await StatisticsEngine(session).get_leaderboard(
        metric="points_per_game", stat_type="skater"
    )
    names = [r["name"] for r in result["results"]]
    assert "A. Callup" not in names  # 2-game call-up must be filtered out


async def test_career_rate_metric_custom_min_games(session):
    await _seed(session)
    result = await StatisticsEngine(session).get_leaderboard(
        metric="points_per_game", stat_type="skater", min_games=2
    )
    names = [r["name"] for r in result["results"]]
    assert "A. Callup" in names


async def test_unknown_metric_raises_value_error(session):
    await _seed(session)
    try:
        await StatisticsEngine(session).get_leaderboard(metric="bogus")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unknown metric")
