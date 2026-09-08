"""Tests for the history engine: per-team season charts, records, streaks."""

from app.models import Champion, PlayoffSeries, Season, Team, TeamSeasonStats
from app.services.history import build_team_season_history, summarize_history


async def _seed(session):
    session.add_all(
        [
            Team(id=1, full_name="Hockey Club", abbreviation="HCL"),
            Season(id=20222023, formatted_id="2022-23"),
            Season(id=20232024, formatted_id="2023-24"),
            Season(id=20242025, formatted_id="2024-25"),
        ]
    )
    await session.flush()
    session.add_all(
        [
            TeamSeasonStats(
                team_id=1, season_id=20222023, game_type=2,
                games_played=82, wins=38, losses=34, ot_losses=5, points=81,
                goals_for=200, goals_against=210,
            ),
            TeamSeasonStats(
                team_id=1, season_id=20232024, game_type=2,
                games_played=82, wins=49, losses=25, ot_losses=8, points=106,
                goals_for=250, goals_against=220,
            ),
            TeamSeasonStats(
                team_id=1, season_id=20242025, game_type=2,
                games_played=82, wins=52, losses=25, ot_losses=5, points=109,
                goals_for=270, goals_against=215,
            ),
            Champion(
                season_id=20242025, winner_team_id=1, runner_team_id=2,
                winner_name="Hockey Club", runner_name="Other",
                champ_wins=4, runner_wins=2,
            ),
            PlayoffSeries(
                season_id=20242025, round_number=3, round_label="Conference Final",
                conference="Eastern", winner_team_id=1, winner_name="Hockey Club",
                loser_team_id=3, loser_name="Third", winner_games=4, loser_games=1,
            ),
            PlayoffSeries(
                season_id=20232024, round_number=3, round_label="Conference Final",
                conference="Western", winner_team_id=4, winner_name="Fourth",
                loser_team_id=1, loser_name="Hockey Club",
                winner_games=4, loser_games=3,
            ),
        ]
    )
    await session.flush()


async def test_history_builds_ascending_rows_with_markers(session):
    await _seed(session)
    history = await build_team_season_history(session, {1})
    seasons = history["seasons"]
    assert [s["season_id"] for s in seasons] == [20222023, 20232024, 20242025]
    assert seasons[-1]["stanley_cup"] is True
    assert seasons[-1]["cup_finalist"] is True
    assert seasons[0]["stanley_cup"] is False
    assert seasons[1]["conference_final"] is True
    assert seasons[2]["conference_final"] is True


async def test_history_points_pct_and_differential(session):
    await _seed(session)
    seasons = (await build_team_season_history(session, {1}))["seasons"]
    first = seasons[0]
    assert first["points_pct"] == round(81 / (82 * 2), 3)
    assert first["goal_differential"] == -10


async def test_summarize_history_records_and_streaks(session):
    await _seed(session)
    history = await build_team_season_history(session, {1})
    records = history["records"]
    assert records["points"]["value"] == 109
    assert records["points"]["season_label"] == "2024-25"
    assert records["wins"]["value"] == 52
    streaks = history["streaks"]
    assert streaks["current_100_point_seasons"] == 2
    assert streaks["longest_100_point_seasons"] == 2
    assert streaks["current_winning_seasons"] == 2  # 2022-23 (.494) breaks the run
    assert streaks["longest_winning_seasons"] == 2
    assert streaks["last_cup_season"] == 20242025
    assert streaks["seasons_since_cup"] == 0


async def test_summarize_history_cup_drought(session):
    rows = [
        {"season_id": 20192020, "points": 78, "points_pct": 0.476, "stanley_cup": True},
        {"season_id": 20202021, "points": 90, "points_pct": 0.549, "stanley_cup": False},
        {"season_id": 20212022, "points": 95, "points_pct": 0.579, "stanley_cup": False},
    ]
    summary = summarize_history(rows)
    assert summary["streaks"]["last_cup_season"] == 20192020
    assert summary["streaks"]["seasons_since_cup"] == 2
    assert summary["streaks"]["current_winning_seasons"] == 2


async def test_summarize_history_no_cup(session):
    rows = [
        {"season_id": 20202021, "points": 90, "points_pct": 0.549, "stanley_cup": False},
    ]
    summary = summarize_history(rows)
    assert summary["streaks"]["last_cup_season"] is None
    assert summary["streaks"]["seasons_since_cup"] is None
