"""Tests for the playoff series history model and endpoint helpers."""

import sqlalchemy

from app.models import PlayoffSeries, Season, Team


async def _seed_conf_final(session):
    session.add_all(
        [
            Season(id=20242025, formatted_id="2024-25"),
            Team(id=13, full_name="Florida Panthers", abbreviation="FLA"),
            Team(id=12, full_name="Carolina Hurricanes", abbreviation="CAR"),
        ]
    )
    await session.flush()
    session.add(
        PlayoffSeries(
            season_id=20242025,
            round_number=3,
            round_label="Conference Final",
            conference="Eastern",
            winner_team_id=13,
            winner_name="Florida Panthers",
            loser_team_id=12,
            loser_name="Carolina Hurricanes",
            winner_games=4,
            loser_games=1,
        )
    )
    await session.flush()


async def test_playoff_series_roundtrip(session):
    await _seed_conf_final(session)
    series = (
        await session.execute(
            sqlalchemy.select(PlayoffSeries).where(
                PlayoffSeries.season_id == 20242025
            )
        )
    ).scalars().one()
    assert series.round_number == 3
    assert series.conference == "Eastern"
    assert series.winner_games == 4
    assert series.loser_games == 1
    assert series.winner_team_id == 13
    assert series.loser_team_id == 12


async def test_playoff_series_uses_reference_names(session):
    await _seed_conf_final(session)
    series = (
        await session.execute(
            sqlalchemy.select(PlayoffSeries).where(
                PlayoffSeries.season_id == 20242025
            )
        )
    ).scalars().one()
    # winner/loser names are authoritative reference data alongside team ids
    assert series.winner_name == "Florida Panthers"
    assert series.loser_name == "Carolina Hurricanes"
