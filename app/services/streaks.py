"""Game-level streak engine for teams (deterministic, offline).

Inputs are game dicts in the same shape the API projects from the ``games``
table: ``game_date``, ``season_id``, ``game_type``, ``home_team_id``,
``away_team_id``, ``home_score``, ``away_score`` and ``ot_sol``. All helpers
are pure so streak semantics are unit-tested exactly.

Semantics match mainstream NHL usage:
  - a *winning streak* is consecutive wins,
  - a *losing streak* counts every loss including OT/shootout losses,
  - a *point streak* counts games with at least one point (wins + OT/SO losses),
  - the "last 10" is the ten most recent games in the window.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

WIN = "W"
LOSS = "L"
OTL = "OTL"


def _result_for(
    *,
    team_score: int | None,
    opponent_score: int | None,
    ot_sol: str | None,
) -> str | None:
    """Result from the perspective of the evaluated team."""
    if team_score is None or opponent_score is None:
        return None
    if team_score > opponent_score:
        return WIN
    # An overtime/shootout loss still earns a point, so it is not a plain L.
    return OTL if ot_sol else LOSS


def team_game_views(games: list[dict[str, Any]], team_id: int) -> list[dict[str, Any]]:
    """Project games so every row is from the given team's perspective.

    Rows are returned in game_date order (stable, oldest first).
    """
    views: list[dict[str, Any]] = []
    for g in sorted(games, key=lambda x: (x.get("game_date") or datetime.min)):
        home = g.get("home_team_id") == team_id
        if home or g.get("away_team_id") == team_id:
            h_score = g.get("home_score")
            a_score = g.get("away_score")
            team_score = h_score if home else a_score
            opponent_score = a_score if home else h_score
            result = _result_for(
                team_score=team_score,
                opponent_score=opponent_score,
                ot_sol=g.get("ot_sol"),
            )
            if result is None:
                continue
            views.append(
                {
                    "game_id": g.get("game_id"),
                    "game_date": g.get("game_date"),
                    "season_id": g.get("season_id"),
                    "game_type": g.get("game_type"),
                    "is_home": home,
                    "result": result,
                    "ot": g.get("ot_sol"),
                    "team_score": team_score,
                    "opponent_score": opponent_score,
                    "opponent_id": g.get("away_team_id") if home else g.get("home_team_id"),
                }
            )
    return views


def _current_streak(results: list[str]) -> dict[str, Any]:
    if not results:
        return {"result": None, "count": 0, "label": ""}
    last = results[-1]
    count = 0
    for r in reversed(results):
        if r != last:
            break
        count += 1
    return {"result": last, "count": count, "label": f"{last}{count}"}


def _longest_same(results: list[str], wanted: str) -> int:
    longest = current = 0
    for r in results:
        if r == wanted:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def compute_team_streaks(views: list[dict[str, Any]]) -> dict[str, Any]:
    """Streak summary over team-perspective game views (ascending by date)."""
    results = [v["result"] for v in views]
    # A losing streak counts every loss (OT/SO losses included); wins break it.
    loss_marks = ["X" if r != WIN else "Y" for r in results]
    # A point streak counts wins and OT/SO losses; regulation losses break it.
    point_marks = ["P" if r in (WIN, OTL) else "X" for r in results]
    return {
        "games_played": len(views),
        "wins": results.count(WIN),
        "ot_losses": results.count(OTL),
        "losses": results.count(LOSS),
        "current_streak": _current_streak(results),
        "longest_win_streak": _longest_same(results, WIN),
        "longest_loss_streak": _longest_same(loss_marks, "X"),
        "longest_point_streak": _longest_same(point_marks, "P"),
        "last_10": {
            "wins": results[-10:].count(WIN),
            "ot_losses": results[-10:].count(OTL),
            "losses": results[-10:].count(LOSS),
        },
    }
