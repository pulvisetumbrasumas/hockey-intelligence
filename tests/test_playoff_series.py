"""Tests for playoff early-round series reconstruction."""

from app.services.playoffs import reconstruct_early_rounds


def _playoff_game(
    season, round_number, letter, away_id, home_id,
    away_abbrev, home_abbrev, away_score, home_score, title,
):
    return {
        "season": season,
        "gameType": 3,
        "seriesStatus": {
            "round": round_number,
            "seriesLetter": letter,
            "seriesTitle": title,
        },
        "awayTeam": {"id": away_id, "abbrev": away_abbrev, "score": away_score},
        "homeTeam": {"id": home_id, "abbrev": home_abbrev, "score": home_score},
    }


def test_reconstruction_picks_the_4_win_team():
    """A conference quarterfinal: the team that wins 4 games wins the series."""
    games = [
        # winner EDM (22) beats CAR (12) 4 games to 2; home side alternates
        _playoff_game(20242025, 1, "D", 22, 12, "EDM", "CAR", 3, 2, "1st Round"),   # EDM
        _playoff_game(20242025, 1, "D", 22, 12, "EDM", "CAR", 2, 1, "1st Round"),   # EDM
        _playoff_game(20242025, 1, "D", 12, 22, "CAR", "EDM", 4, 3, "1st Round"),   # CAR
        _playoff_game(20242025, 1, "D", 12, 22, "CAR", "EDM", 1, 3, "1st Round"),   # EDM
        _playoff_game(20242025, 1, "D", 22, 12, "EDM", "CAR", 2, 4, "1st Round"),   # CAR
        _playoff_game(20242025, 1, "D", 12, 22, "CAR", "EDM", 2, 4, "1st Round"),   # EDM
    ]
    series = reconstruct_early_rounds(games)
    assert len(series) == 1
    s = series[0]
    assert s["round_number"] == 1
    assert s["conference"] == "Eastern"  # series letter D
    assert s["winner_team_id"] == 22
    assert s["loser_team_id"] == 12
    assert s["winner_games"] == 4
    assert s["loser_games"] == 2


def test_skips_conference_finals_and_cup_final():
    games = [
        _playoff_game(20242025, 3, "M", 13, 12, "FLA", "CAR", 0, 4, "Conference Finals"),
        _playoff_game(20242025, 4, "F", 13, 22, "FLA", "EDM", 2, 4, "Stanley Cup Final"),
    ]
    assert reconstruct_early_rounds(games) == []


def test_conference_mapping_for_second_round():
    games = [
        # K = Western (COL @ DAL), J = Eastern (CAR @ NYR)
        _playoff_game(20242025, 2, "K", 21, 25, "COL", "DAL", 1, 4, "2nd Round"),
        _playoff_game(20242025, 2, "J", 12, 3, "CAR", "NYR", 2, 3, "2nd Round"),
    ]
    by_letter = {s["conference"] for s in reconstruct_early_rounds(games)}
    assert by_letter == {"Eastern", "Western"}


def test_seasons_are_grouped_separately():
    games = [
        _playoff_game(20232024, 1, "A", 13, 14, "FLA", "TBL", 4, 1, "1st Round"),
        _playoff_game(20242025, 1, "A", 13, 14, "FLA", "TBL", 4, 2, "1st Round"),
    ]
    series = reconstruct_early_rounds(games)
    assert {s["season_id"] for s in series} == {20232024, 20242025}
    assert all(s["winner_games"] == 1 for s in series)


def test_games_without_scores_do_not_break_series():
    games = [
        _playoff_game(20242025, 1, "B", 10, 6, "TOR", "BOS", 4, 3, "1st Round"),
        {"season": 20242025, "gameType": 3, "gameState": "LIVE",
         "seriesStatus": {"round": 1, "seriesLetter": "B", "seriesTitle": "1st Round"},
         "awayTeam": {"id": 10, "abbrev": "TOR"}, "homeTeam": {"id": 6, "abbrev": "BOS"}},
    ]
    series = reconstruct_early_rounds(games)
    assert len(series) == 1
    assert series[0]["winner_games"] == 1


def test_4_0_sweep_still_records_the_loser():
    games = [
        _playoff_game(20252026, 1, "C", 15, 3, "WSH", "NYR", 1, 4, "1st Round"),
        _playoff_game(20252026, 1, "C", 15, 3, "WSH", "NYR", 2, 5, "1st Round"),
        _playoff_game(20252026, 1, "C", 3, 15, "NYR", "WSH", 4, 1, "1st Round"),
        _playoff_game(20252026, 1, "C", 3, 15, "NYR", "WSH", 3, 2, "1st Round"),
    ]
    series = reconstruct_early_rounds(games)
    assert len(series) == 1
    s = series[0]
    assert s["winner_team_id"] == 3
    assert s["loser_team_id"] == 15
    assert s["winner_games"] == 4
    assert s["loser_games"] == 0
