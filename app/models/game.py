from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Integer, String, Column, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.player import Player
    from app.models.season import Season
    from app.models.team import Team


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("seasons.id"), index=True
    )
    game_type: Mapped[Optional[int]] = mapped_column(Integer)
    game_date: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    home_team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id"), index=True
    )
    away_team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id"), index=True
    )
    home_team_code: Mapped[Optional[str]] = mapped_column(String(10))
    away_team_code: Mapped[Optional[str]] = mapped_column(String(10))
    home_score: Mapped[Optional[int]] = mapped_column(Integer)
    away_score: Mapped[Optional[int]] = mapped_column(Integer)
    venue: Mapped[Optional[str]] = mapped_column(String(200))
    ot_sol: Mapped[Optional[str]] = mapped_column(String(10))
    attendance: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[Optional[str]] = mapped_column(String(20))

    home_team: Mapped[Optional["Team"]] = relationship("Team", foreign_keys=[home_team_id])
    away_team: Mapped[Optional["Team"]] = relationship("Team", foreign_keys=[away_team_id])
    season: Mapped[Optional["Season"]] = relationship("Season")

    def __repr__(self):
        return f"<Game(id={self.id}, {self.away_team_code}@{self.home_team_code})>"


class GameEvent(Base):
    __tablename__ = "game_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("games.id"), index=True
    )
    event_type: Mapped[Optional[str]] = mapped_column(String(30), index=True)
    period: Mapped[Optional[int]] = mapped_column(Integer)
    period_time: Mapped[Optional[str]] = mapped_column(String(10))
    strength: Mapped[Optional[str]] = mapped_column(String(20))
    strength_code: Mapped[Optional[str]] = mapped_column(String(5))
    team_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"))
    player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), index=True
    )
    assist_1_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("players.id"))
    assist_2_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("players.id"))
    secondary_ids: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    sort_order: Mapped[Optional[int]] = mapped_column(Integer)

    game: Mapped[Optional["Game"]] = relationship("Game", backref=None)
    player: Mapped[Optional["Player"]] = relationship(
        "Player", foreign_keys=[player_id], backref=None
    )