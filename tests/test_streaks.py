"""Tests for the game-level streak engine and team game projection."""

from app.services.streaks import (
    LOSS,
    OTL,
    WIN,
    _result_for,
    compute_team_streaks,
    team_game_views,
)


def _game(gid, date, home, away, hs, as_, ot=None, game_type=2):
    return {
        "game_id": gid,
        "game_date": date,
        "season_id": 20242025,
        "game_type": game_type,
        "home_team_id": home,
        "away_team_id": away,
        "home_score": hs,
        "away_score": as_,
        "ot_sol": ot,
    }


def _t1(home: bool, gid, date, team_score, opp_score, ot=None):
    """A game for team 1 with ``team_score`` vs ``opponent_score``."""
    if home:
        return _game(gid, date, home=1, away=2, hs=team_score, as_=opp_score, ot=ot)
    return _game(gid, date, home=2, away=1, hs=opp_score, as_=team_score, ot=ot)


def test_result_for_home_team():
    assert _result_for(team_score=3, opponent_score=1, ot_sol=None) == WIN
    assert _result_for(team_score=1, opponent_score=3, ot_sol=None) == LOSS
    assert _result_for(team_score=2, opponent_score=3, ot_sol="OT") == OTL
    assert _result_for(team_score=2, opponent_score=3, ot_sol="SO") == OTL
    assert _result_for(team_score=None, opponent_score=2, ot_sol=None) is None


def test_team_game_views_only_owns_row_and_orders_ascending():
    games = [
        _t1(True, 1, "2024-10-05", 4, 1),                    # home W
        _t1(False, 2, "2024-10-03", 1, 2),                   # away L
        _game(3, "2024-10-04", home=3, away=4, hs=1, as_=2),  # unrelated
    ]
    views = team_game_views(games, 1)
    assert [v["game_date"] for v in views] == ["2024-10-03", "2024-10-05"]
    assert views[0]["is_home"] is False
    assert views[0]["result"] == LOSS
    assert views[1]["is_home"] is True
    assert views[1]["result"] == WIN


def test_streak_summary_semantics():
    # W W L OTL W W W  (OTL does NOT extend the losing streak intent here;
    # it is a distinct result that also contributes a point)
    games = [
        _t1(True, 1, "2024-10-05", 4, 1),       # W
        _t1(False, 2, "2024-10-07", 5, 1),      # W
        _t1(False, 3, "2024-10-09", 3, 4),      # L
        _t1(True, 4, "2024-10-11", 2, 3, ot="OT"),  # OTL
        _t1(True, 5, "2024-10-13", 3, 2),       # W
        _t1(True, 6, "2024-10-15", 5, 4),       # W
    ]
    summary = compute_team_streaks(team_game_views(games, 1))
    assert summary["wins"] == 4
    assert summary["ot_losses"] == 1
    assert summary["losses"] == 1
    assert summary["current_streak"] == {"result": WIN, "count": 2, "label": "W2"}
    assert summary["longest_win_streak"] == 2
    assert summary["longest_loss_streak"] == 2  # the L followed by the OTL
    assert summary["longest_point_streak"] == 3  # OTL W W tail
    assert summary["last_10"] == {"wins": 4, "ot_losses": 1, "losses": 1}


def test_streak_summary_otl_extends_point_streak():
    # L OTL W OTL  → point streak = 3 (OTL W OTL), losing streak = 2 (L+OTL)
    games = [
        _t1(True, 1, "2024-10-05", 1, 3),
        _t1(False, 2, "2024-10-07", 2, 3, ot="OT"),
        _t1(True, 3, "2024-10-09", 4, 1),
        _t1(False, 4, "2024-10-11", 3, 4, ot="SO"),
    ]
    summary = compute_team_streaks(team_game_views(games, 1))
    assert summary["longest_loss_streak"] == 2
    assert summary["longest_point_streak"] == 3
    assert summary["current_streak"] == {"result": OTL, "count": 1, "label": "OTL1"}


def test_streak_summary_current_loss_breakdown_last10():
    # four wins then two regulation losses at the tail
    games = [
        _t1(True, 1, "2024-10-05", 4, 1),
        _t1(False, 2, "2024-10-07", 3, 2),
        _t1(True, 3, "2024-10-09", 2, 0),
        _t1(False, 4, "2024-10-11", 5, 3),
        _t1(True, 5, "2024-10-13", 1, 4),
        _t1(False, 6, "2024-10-15", 2, 3),
    ]
    summary = compute_team_streaks(team_game_views(games, 1))
    assert summary["current_streak"] == {"result": LOSS, "count": 2, "label": "L2"}
    assert summary["longest_win_streak"] == 4
    assert summary["longest_loss_streak"] == 2
    assert summary["last_10"] == {"wins": 4, "ot_losses": 0, "losses": 2}


def test_streak_summary_empty_and_absent_games():
    assert compute_team_streaks([])["current_streak"]["count"] == 0
    views = team_game_views(
        [_game(1, "2024-10-05", home=1, away=2, hs=None, as_=None)], 1
    )
    assert views == []
