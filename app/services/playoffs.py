"""Playoff early-round series reconstruction (deterministic, offline).

The NHL web API does not expose a series-history endpoint, but the weekly
schedule feed carries every finalized playoff game with a ``seriesStatus``
block (round, series letter, score). Grouping those games by season + round +
series letter reproduces each best-of-seven series; the team with more wins
is the series winner. This module does the reconstruction from raw game
dicts so it can be unit-tested without any network or database access.

Round 1-2 series letters pin a conference deterministically (verified against
both the 1993-2013 two-division alignment and the modern 2013+ alignment):

    A-D   Eastern   (first round)      I, J   Eastern  (second round)
    E-H   Western   (first round)      K, L   Western  (second round)
"""

from __future__ import annotations

from typing import Any

ROUND_LETTER_CONFERENCE: dict[str, str] = {
    "A": "Eastern",
    "B": "Eastern",
    "C": "Eastern",
    "D": "Eastern",
    "I": "Eastern",
    "J": "Eastern",
    "E": "Western",
    "F": "Western",
    "G": "Western",
    "H": "Western",
    "K": "Western",
    "L": "Western",
}

# The Stanley Cup Final and conference finals are sourced from the champions
# table and the hand-verified conference-final rows respectively; this module
# only ever restores the qualifying rounds.
RESTORED_ROUNDS = (1, 2)


def _conference_for(round_number: int, letter: str | None) -> str | None:
    if letter is None:
        return None
    return ROUND_LETTER_CONFERENCE.get(letter.upper())


def reconstruct_early_rounds(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Derive first- and second-round series from raw playoff game dicts.

    Each game dict is expected to expose ``season``, ``seriesStatus`` and the
    ``homeTeam``/``awayTeam`` blocks with ``id`` and ``score``. Returns series
    descriptors (winner/loser team ids + game counts) keyed for the database;
    names are left for the caller to resolve.
    """
    buckets: dict[tuple[int, int, str], dict[str, Any]] = {}

    for g in games:
        status = g.get("seriesStatus") or {}
        round_number = status.get("round")
        letter = status.get("seriesLetter")
        season = g.get("season")
        if (
            round_number not in RESTORED_ROUNDS
            or not letter
            or season is None
        ):
            continue
        home = g.get("homeTeam") or {}
        away = g.get("awayTeam") or {}
        home_id = home.get("id")
        away_id = away.get("id")
        if home_id is None or away_id is None:
            continue

        key = (season, round_number, str(letter).upper())
        bucket = buckets.setdefault(
            key,
            {
                "season_id": season,
                "round_number": round_number,
                "round_label": status.get("seriesTitle") or f"Round {round_number}",
                "conference": _conference_for(round_number, letter),
                "team_ids": set(),
                "teams": {},
                "wins": {},
                "games": 0,
            },
        )
        bucket["team_ids"].add(home_id)
        bucket["team_ids"].add(away_id)
        bucket["teams"].setdefault(home_id, {"id": home_id, "abbrev": home.get("abbrev")})
        bucket["teams"].setdefault(away_id, {"id": away_id, "abbrev": away.get("abbrev")})

        home_score = home.get("score")
        away_score = away.get("score")
        if home_score is None or away_score is None:
            continue
        bucket["games"] += 1
        if home_score > away_score:
            bucket["wins"][home_id] = bucket["wins"].get(home_id, 0) + 1
        else:
            bucket["wins"][away_id] = bucket["wins"].get(away_id, 0) + 1

    series: list[dict[str, Any]] = []
    for bucket in buckets.values():
        if not bucket["team_ids"]:
            continue
        # Rank every participant, not just the ones who won a game — a 4-0
        # sweep would otherwise leave the losing team out of the tally.
        ranked = sorted(
            ((tid, bucket["wins"].get(tid, 0)) for tid in bucket["team_ids"]),
            key=lambda kv: kv[1],
            reverse=True,
        )
        winner_id, winner_wins = ranked[0]
        loser_id, loser_wins = ranked[1] if len(ranked) > 1 else (None, 0)
        series.append(
            {
                "season_id": bucket["season_id"],
                "round_number": bucket["round_number"],
                "round_label": bucket["round_label"],
                "conference": bucket["conference"],
                "winner_team_id": winner_id,
                "winner_abbrev": bucket["teams"].get(winner_id, {}).get("abbrev"),
                "loser_team_id": loser_id,
                "loser_abbrev": bucket["teams"].get(loser_id, {}).get("abbrev"),
                "winner_games": winner_wins,
                "loser_games": loser_wins,
                "games_played": bucket["games"],
            }
        )
    series.sort(key=lambda s: (s["season_id"], s["round_number"], s["conference"] or ""))
    return series
