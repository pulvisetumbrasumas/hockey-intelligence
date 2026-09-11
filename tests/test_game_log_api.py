"""HTTP tests for the per-team game log + streak endpoint.

The route under test: ``GET /api/teams/{team_id}/games``. It lives in
``app.api.routes.teams``, so the DB dependency is overridden there with a
fresh in-memory SQLite database.
"""

import datetime

import httpx
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.api.routes.teams as teams_route
from app.database.connection import Base
from app.main import app
from app.models import Game, Season, Team


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as s:
        s.add_all(
            [
                Season(id=20242025, formatted_id="2024-25"),
                Team(id=1, full_name="New Jersey Devils", abbreviation="NJD"),
                Team(id=12, full_name="Carolina Hurricanes", abbreviation="CAR"),
            ]
        )
        await s.flush()
        s.add_all(
            [
                Game(
                    id=1, game_type=2, season_id=20242025,
                    game_date=datetime.date(2024, 10, 10),
                    home_team_id=1, away_team_id=12,
                    home_team_code="NJD", away_team_code="CAR",
                    home_score=3, away_score=2,
                ),
                Game(
                    id=2, game_type=2, season_id=20242025,
                    game_date=datetime.date(2024, 10, 12),
                    home_team_id=1, away_team_id=12,
                    home_team_code="NJD", away_team_code="CAR",
                    home_score=2, away_score=3, ot_sol="OT",
                ),
                Game(
                    id=3, game_type=2, season_id=20242025,
                    game_date=datetime.date(2024, 10, 14),
                    home_team_id=1, away_team_id=12,
                    home_team_code="NJD", away_team_code="CAR",
                    home_score=1, away_score=4,
                ),
                # A playoff (gameType 3) win for Carolina must NOT count
                # toward the regular-season streak summary of either club.
                Game(
                    id=4, game_type=3, season_id=20242025,
                    game_date=datetime.date(2025, 4, 20),
                    home_team_id=12, away_team_id=1,
                    home_team_code="CAR", away_team_code="NJD",
                    home_score=4, away_score=1,
                ),
            ]
        )
        await s.commit()

    async def override_db():
        async with factory() as sess:
            yield sess

    app.dependency_overrides[teams_route.get_db] = override_db
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.clear()
    await engine.dispose()


async def test_team_games_streaks_ignore_playoffs(client):
    r = await client.get("/api/teams/1/games")
    assert r.status_code == 200
    d = r.json()
    assert d["team_id"] == 1
    assert d["season_id"] == 20242025
    assert [c["season_id"] for c in d["coverage"]] == [20242025]
    assert len(d["games"]) == 4  # log includes playoff games
    assert d["games"][0]["game_type"] == 2
    # The closing playoff game (Carolina's 4-1 home win) reads as an L here.
    assert d["games"][-1]["game_type"] == 3 and d["games"][-1]["result"] == "L"

    st = d["streaks"]
    assert st["games_played"] == 3  # playoff game excluded
    assert st["wins"] == 1
    assert st["ot_losses"] == 1
    assert st["losses"] == 1
    assert st["current_streak"] == {"result": "L", "count": 1, "label": "L1"}
    assert st["longest_win_streak"] == 1
    assert st["longest_point_streak"] == 2  # the OT loss earns a point
    assert st["longest_loss_streak"] == 2  # OT loss follows the regulation loss


async def test_team_games_perspective_and_venue(client):
    r = await client.get("/api/teams/12/games")
    d = r.json()
    # Carolina's perspective on the first game (a 3-2 away loss) must be a
    # loss with its own score first — not the home team's numbers.
    away = d["games"][0]
    assert away["is_home"] is False
    assert away["opponent"]["name"] == "New Jersey Devils"
    assert away["result"] == "L"
    assert away["team_score"] == 2 and away["opponent_score"] == 3
    # The final playoff game is Carolina's 4-1 home win.
    home = d["games"][-1]
    assert home["is_home"] is True
    assert home["result"] == "W"
    assert home["team_score"] == 4 and home["opponent_score"] == 1


async def test_team_games_unknown_team_404(client):
    r = await client.get("/api/teams/99999/games")
    assert r.status_code == 404


async def test_team_games_unknown_season_returns_empty(client):
    r = await client.get("/api/teams/1/games?season_id=19901991")
    d = r.json()
    assert d["season_id"] == 19901991
    assert d["games"] == []
    assert d["streaks"] is None  # no games on record for that season, no crash
