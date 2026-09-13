from pydantic import BaseModel, Field


class SimSeasonRequest(BaseModel):
    """What was purchased for the toy season — buy-then-play, not betting."""

    skaters: list[int] = Field(default_factory=list)
    goalies: list[int] = Field(default_factory=list)
    teams: list[int] = Field(default_factory=list)
    seed: int | None = None