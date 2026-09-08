from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.player import Player
    from app.models.season import Season
    from app.models.team import Team


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("seasons.id"), index=True
    )
    game_type: Mapped[int | None] = mapped_column(Integer)
    game_date: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    home_team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teams.id"), index=True
    )
    away_team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teams.id"), index=True
    )
    home_team_code: Mapped[str | None] = mapped_column(String(10))
    away_team_code: Mapped[str | None] = mapped_column(String(10))
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    venue: Mapped[str | None] = mapped_column(String(200))
    ot_sol: Mapped[str | None] = mapped_column(String(10))
    attendance: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(20))

    home_team: Mapped[Team | None] = relationship("Team", foreign_keys=[home_team_id])
    away_team: Mapped[Team | None] = relationship("Team", foreign_keys=[away_team_id])
    season: Mapped[Season | None] = relationship("Season")

    def __repr__(self):
        return f"<Game(id={self.id}, {self.away_team_code}@{self.home_team_code})>"


class GameEvent(Base):
    __tablename__ = "game_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("games.id"), index=True
    )
    event_type: Mapped[str | None] = mapped_column(String(30), index=True)
    period: Mapped[int | None] = mapped_column(Integer)
    period_time: Mapped[str | None] = mapped_column(String(10))
    strength: Mapped[str | None] = mapped_column(String(20))
    strength_code: Mapped[str | None] = mapped_column(String(5))
    team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"))
    player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id"), index=True
    )
    assist_1_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("players.id"))
    assist_2_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("players.id"))
    secondary_ids: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int | None] = mapped_column(Integer)

    game: Mapped[Game | None] = relationship("Game", backref=None)
    player: Mapped[Player | None] = relationship(
        "Player", foreign_keys=[player_id], backref=None
    )
