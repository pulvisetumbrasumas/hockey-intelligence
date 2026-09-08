import httpx
from typing import Any
from urllib.parse import quote

from app.core.config import get_settings
from app.providers.base import HockeyDataProvider

settings = get_settings()


class NHLDataProvider(HockeyDataProvider):
    """Provider backed by the public NHL stats & web APIs.

    The NHL Stats API (api.nhle.com/stats/rest/en) provides bulk season-level
    statistics. The NHL Web API (api-web.nhle.com/v1) provides player bios,
    current rankings and schedules.

    This API is provided by the NHL for informational purposes. Data
    licensing should be reviewed before redistributing."
    """

    name = "nhl"
    source_url = settings.nhl_stats_api_base

    def __init__(self) -> None:
        self.stats_base = settings.nhl_stats_api_base
        self.web_base = settings.nhl_web_api_base
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _stats_get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(f"{self.stats_base}/{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json()

    async def _web_get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(f"{self.web_base}/{endpoint}", params=params or {})
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _sort(prop: str, direction: str = "ASC") -> str:
        # Return the raw JSON; httpx percent-encodes params correctly.
        return f'[{{"property":"{prop}","direction":"{direction}"}}]'

    async def get_franchises(self) -> list[dict[str, Any]]:
        data = await self._stats_get("franchise", {"start": 0, "limit": 200})
        return data.get("data", [])

    async def get_seasons(self) -> list[dict[str, Any]]:
        data = await self._stats_get("season", {"start": 0, "limit": 200})
        return data.get("data", [])

    async def get_teams(self) -> list[dict[str, Any]]:
        data = await self._stats_get("team", {"start": 0, "limit": 200})
        return data.get("data", [])

    async def get_player_bios(self, player_ids: list[int]) -> dict[int, dict[str, Any]]:
        """Fetch player bios from the web API landing pages."""
        result: dict[int, dict[str, Any]] = {}
        client = await self._get_client()
        for pid in player_ids:
            try:
                resp = await client.get(f"{self.web_base}/player/{pid}/landing")
                if resp.status_code == 200:
                    result[pid] = resp.json()
            except httpx.HTTPError:
                continue
        return result

    async def get_skater_stats(
        self, season_id: int, game_type: int = 2, start: int = 0, limit: int = 100
    ) -> tuple[list[dict[str, Any]], int]:
        cayenne = (
            f"seasonId<={season_id} and seasonId>={season_id} and gameTypeId={game_type}"
        )
        data = await self._stats_get(
            "skater/summary",
            {
                "isAggregate": "false",
                "isGame": "false",
                "sort": self._sort("points", "DESC"),
                "start": start,
                "limit": limit,
                "cayenneExp": cayenne,
            },
        )
        return data.get("data", []), data.get("total", 0)

    async def get_goalie_stats(
        self, season_id: int, game_type: int = 2, start: int = 0, limit: int = 100
    ) -> tuple[list[dict[str, Any]], int]:
        cayenne = (
            f"seasonId<={season_id} and seasonId>={season_id} and gameTypeId={game_type}"
        )
        data = await self._stats_get(
            "goalie/summary",
            {
                "isAggregate": "false",
                "isGame": "false",
                "sort": self._sort("wins", "DESC"),
                "start": start,
                "limit": limit,
                "cayenneExp": cayenne,
            },
        )
        return data.get("data", []), data.get("total", 0)

    async def get_team_stats(
        self, season_id: int, game_type: int = 2, start: int = 0, limit: int = 100
    ) -> tuple[list[dict[str, Any]], int]:
        cayenne = (
            f"seasonId<={season_id} and seasonId>={season_id} and gameTypeId={game_type}"
        )
        data = await self._stats_get(
            "team/summary",
            {
                "isAggregate": "false",
                "isGame": "false",
                "sort": self._sort("points", "DESC"),
                "start": start,
                "limit": limit,
                "cayenneExp": cayenne,
            },
        )
        return data.get("data", []), data.get("total", 0)

    async def get_games(self, season_id: int) -> list[dict[str, Any]]:
        """Fetch schedule for a season from the web API."""
        season_str = f"{season_id}"
        data = await self._web_get("season", {"season": season_str})
        games = data.get("games", [])
        # The web API season endpoint may paginate via 'nextStartDate'
        out = list(games)
        next_start = data.get("nextStartDate")
        guard = 0
        while next_start and guard < 50:
            data = await self._web_get(
                "season", {"season": season_str, "startDate": next_start}
            )
            out.extend(data.get("games", []))
            next_start = data.get("nextStartDate")
            guard += 1
        return out

    async def get_playoff_stats(self, player_id: int) -> dict[str, Any]:
        return await self._web_get("player", {"playerId": str(player_id)})