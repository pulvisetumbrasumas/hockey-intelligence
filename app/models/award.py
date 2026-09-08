from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base


class Award(Base):
    __tablename__ = "awards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[Optional[str]] = mapped_column(String(20))
    name: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    short_name: Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(String(500))


class PlayerAward(Base):
    __tablename__ = "player_awards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), index=True
    )
    award_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("awards.id"), index=True
    )
    season_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("seasons.id"), index=True
    )
    team_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"))
    is_finalist: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    rank: Mapped[Optional[int]] = mapped_column(Integer)
    vote_pct: Mapped[Optional[int]] = mapped_column(Integer)

    player: Mapped[Optional["Player"]] = relationship("Player")
    award: Mapped[Optional["Award"]] = relationship("Award")
    season: Mapped[Optional["Season"]] = relationship("Season")
    team: Mapped[Optional["Team"]] = relationship("Team")


from app.models.player import Player  # noqa: E402
from app.models.season import Season  # noqa: E402
from app.models.team import Team  # noqa: E402