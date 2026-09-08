from pydantic import BaseModel, Field
from typing import Any, Optional


class PlayerOut(BaseModel):
    player_id: int
    full_name: str
    position: Optional[str] = None
    birth_date: Optional[str] = None
    birth_city: Optional[str] = None
    birth_country: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[int] = None
    shoots_catches: Optional[str] = None
    draft_year: Optional[int] = None
    draft_round: Optional[int] = None
    draft_overall: Optional[int] = None
    active: bool = False


class PlayerSearchResult(BaseModel):
    player_id: int
    full_name: str
    position: Optional[str] = None
    active: bool = False


class SearchResponse(BaseModel):
    query: str
    players: list[PlayerSearchResult] = []
    teams: list[dict[str, Any]] = []
    count: int = 0


class TeamOut(BaseModel):
    team_id: int
    full_name: str
    abbreviation: Optional[str] = None
    franchise: Optional[dict[str, Any]] = None
    active: bool = False
    identities: list[dict[str, Any]] = []


class AIQuestionIn(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class AIQuestionOut(BaseModel):
    answer: str
    model: str
    tool_calls: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    truncated: bool = False