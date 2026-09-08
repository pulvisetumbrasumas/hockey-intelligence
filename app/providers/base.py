from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class HockeyDataProvider(ABC):
    """Abstract interface for hockey data providers.

    Additional providers (licensed APIs, public datasets, historical
    databases) can be implemented without restructuring the application.
    """

    name: str = "base"
    source_url: str = ""

    @abstractmethod
    async def get_franchises(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_seasons(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_teams(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_player_bios(self, player_ids: list[int]) -> dict[int, dict[str, Any]]: ...

    @abstractmethod
    async def get_skater_stats(
        self, season_id: int, game_type: int = 2, start: int = 0, limit: int = 100
    ) -> tuple[list[dict[str, Any]], int]: ...

    @abstractmethod
    async def get_goalie_stats(
        self, season_id: int, game_type: int = 2, start: int = 0, limit: int = 100
    ) -> tuple[list[dict[str, Any]], int]: ...

    @abstractmethod
    async def get_team_stats(
        self, season_id: int, game_type: int = 2, start: int = 0, limit: int = 100
    ) -> tuple[list[dict[str, Any]], int]: ...

    @abstractmethod
    async def get_games(self, season_id: int) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_playoff_stats(self, player_id: int) -> dict[str, Any]: ...