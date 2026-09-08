from typing import Any

from pydantic import BaseModel, Field


class PlayerOut(BaseModel):
    player_id: int
    full_name: str
    position: str | None = None
    nhl_id: int | None = None
    headshot: str | None = None
    hero: str | None = None
    team_abbreviation: str | None = None
    birth_date: str | None = None
    birth_city: str | None = None
    birth_country: str | None = None
    height: str | None = None
    weight: int | None = None
    shoots_catches: str | None = None
    draft_year: int | None = None
    draft_round: int | None = None
    draft_overall: int | None = None
    active: bool = False


class PlayerSearchResult(BaseModel):
    player_id: int
    full_name: str
    position: str | None = None
    nhl_id: int | None = None
    headshot: str | None = None
    hero: str | None = None
    team_abbreviation: str | None = None
    active: bool = False


class SearchResponse(BaseModel):
    query: str
    players: list[PlayerSearchResult] = []
    teams: list[dict[str, Any]] = []
    franchises: list[dict[str, Any]] = []
    count: int = 0


class TeamOut(BaseModel):
    team_id: int
    full_name: str
    abbreviation: str | None = None
    franchise: dict[str, Any] | None = None
    active: bool = False
    identities: list[dict[str, Any]] = []
    championships: list[dict[str, Any]] = []
    cup_count: int = 0


class AIQuestionIn(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class AIQuestionOut(BaseModel):
    answer: str
    model: str
    tool_calls: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    truncated: bool = False
