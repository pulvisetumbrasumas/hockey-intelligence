"""Tests for the AI tool resolvers (name/ID resolution against the database)."""

from app.models.player import Player
from app.models.stats import GoalieSeasonStats, PlayerSeasonStats
from app.services.ai.tools import ToolResults


async def _seed(session):
    session.add_all(
        [
            Player(id=1, nhl_id=1, full_name="Connor McDavid", first_name="Connor",
                   last_name="McDavid", position_code="C", is_goalie=0),
            Player(id=2, nhl_id=2, full_name="Jack McDavid", first_name="Jack",
                   last_name="McDavid", position_code="C", is_goalie=0),
            Player(id=3, nhl_id=3, full_name="Artemi Panarin", first_name="Artemi",
                   last_name="Panarin", position_code="L", is_goalie=0),
            Player(id=4, nhl_id=4, full_name="G. Starter", first_name="G.",
                   last_name="Starter", position_code="G", is_goalie=1),
            PlayerSeasonStats(player_id=1, season_id=20242025, game_type=2,
                              team_abbrevs="EDM", games_played=67, goals=26,
                              assists=74, points=100),
            PlayerSeasonStats(player_id=3, season_id=20242025, game_type=2,
                              team_abbrevs="NYR", games_played=80, goals=37,
                              assists=52, points=89),
            GoalieSeasonStats(player_id=4, season_id=20242025, game_type=2,
                              team_abbrevs="TOT", games_played=55, save_pct=0.9234,
                              saves=9234, shots_against=10000),
        ]
    )
    await session.flush()


async def test_resolve_player_by_full_name(session):
    await _seed(session)
    resolver = ToolResults(session)
    pid, err = await resolver._resolve_player({"full_name": "Connor McDavid"})
    assert err == {}
    assert pid == 1


async def test_resolve_player_ambiguous_name_returns_error(session):
    await _seed(session)
    resolver = ToolResults(session)
    pid, err = await resolver._resolve_player({"full_name": "McDavid"})
    assert pid is None
    assert "Ambiguous" in err["error"]


async def test_resolve_player_not_found_returns_error(session):
    await _seed(session)
    resolver = ToolResults(session)
    pid, err = await resolver._resolve_player({"full_name": "Nobody Famous"})
    assert pid is None
    assert "not found" in err["error"]


async def test_get_player_by_name(session):
    await _seed(session)
    result = await ToolResults(session)._handle_get_player({"full_name": "Connor McDavid"})
    assert result["player_id"] == 1
    assert result["full_name"] == "Connor McDavid"


async def test_get_player_by_id(session):
    await _seed(session)
    result = await ToolResults(session)._handle_get_player({"player_id": "3"})
    assert result["full_name"] == "Artemi Panarin"


async def test_get_player_season_stats_by_name(session):
    await _seed(session)
    result = await ToolResults(session)._handle_get_player_season_stats(
        {"full_name": "Connor McDavid", "season_id": 20242025}
    )
    assert result["skater"]["points"] == 100


async def test_get_player_season_stats_missing_returns_error(session):
    await _seed(session)
    result = await ToolResults(session)._handle_get_player_season_stats(
        {"full_name": "Nobody Famous", "season_id": 20242025}
    )
    assert "error" in result


async def test_compare_players_by_names(session):
    await _seed(session)
    result = await ToolResults(session)._handle_compare_players(
        {"player_names": ["Connor McDavid", "Artemi Panarin"]}
    )
    names = {p["name"] for p in result["players"]}
    assert names == {"Connor McDavid", "Artemi Panarin"}
    assert "winner" not in result


async def test_compare_players_with_fake_id_returns_empty_data_not_crash(session):
    await _seed(session)
    result = await ToolResults(session)._handle_compare_players(
        {"player_ids": [99999999]}
    )
    assert "error" in result  # needs at least 2 players


async def test_search_players_finds_substring(session):
    await _seed(session)
    result = await ToolResults(session)._handle_search_players({"query": "mcda"})
    names = {m["full_name"] for m in result["matches"]}
    assert "Connor McDavid" in names


async def test_unknown_tool_returns_error(session):
    result = await ToolResults(session)._execute("do_anything", {})
    assert result["error"] == "Unknown tool: do_anything"


async def test_get_player_career_stats_via_execute_by_name(session):
    await _seed(session)
    result = await ToolResults(session)._execute(
        "get_player_career_stats", {"full_name": "Connor McDavid"}
    )
    assert result["regular_season"]["points"] == 100


async def test_get_league_leaders_season(session):
    await _seed(session)
    result = await ToolResults(session)._handle_get_league_leaders(
        {"stat": "points", "season_id": 20242025}
    )
    assert result["results"][0]["name"] == "Connor McDavid"
    assert result["results"][0]["value"] == 100


async def test_get_league_leaders_career_goalies(session):
    await _seed(session)
    result = await ToolResults(session)._handle_get_league_leaders(
        {"stat": "save_pct", "stat_type": "goalie"}
    )
    assert result["results"][0]["name"] == "G. Starter"
    assert result["results"][0]["value"] == 0.9234


async def test_get_league_leaders_returns_error_on_bad_stat(session):
    await _seed(session)
    result = await ToolResults(session)._handle_get_league_leaders(
        {"stat": "mcguffins"}
    )
    assert "error" in result
