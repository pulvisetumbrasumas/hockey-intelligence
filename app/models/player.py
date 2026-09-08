from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.stats import GoalieSeasonStats, PlayerSeasonStats


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    nhl_id: Mapped[int | None] = mapped_column(Integer)
    first_name: Mapped[str | None] = mapped_column(String(100), index=True)
    last_name: Mapped[str | None] = mapped_column(String(100), index=True)
    full_name: Mapped[str | None] = mapped_column(String(200), index=True)
    position_code: Mapped[str | None] = mapped_column(String(5), index=True)
    primary_position: Mapped[str | None] = mapped_column(String(50))
    birth_date: Mapped[datetime | None] = mapped_column(DateTime)
    birth_city: Mapped[str | None] = mapped_column(String(100))
    birth_country: Mapped[str | None] = mapped_column(String(100))
    height: Mapped[str | None] = mapped_column(String(20))
    weight: Mapped[int | None] = mapped_column(Integer)
    shoots_catches: Mapped[str | None] = mapped_column(String(1))
    is_goalie: Mapped[int | None] = mapped_column(Integer, default=0)
    is_rookie: Mapped[int | None] = mapped_column(Integer, default=0)
    draft_year: Mapped[int | None] = mapped_column(Integer)
    draft_round: Mapped[int | None] = mapped_column(Integer)
    draft_overall: Mapped[int | None] = mapped_column(Integer)
    draft_team: Mapped[str | None] = mapped_column(String(100))
    active: Mapped[int | None] = mapped_column(Integer, default=1)

    season_stats: Mapped[list[PlayerSeasonStats]] = relationship(
        back_populates="player",
    )
    goalie_stats: Mapped[list[GoalieSeasonStats]] = relationship(
        back_populates="player",
    )

    def __repr__(self):
        return f"<Player(id={self.id}, name='{self.full_name}')>"


class PlayerPosition(Base):
    __tablename__ = "player_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("players.id"), index=True)
    position: Mapped[str | None] = mapped_column(String(50))
    seasons: Mapped[str | None] = mapped_column(String(50))
    games: Mapped[int | None] = mapped_column(Integer)
    goals: Mapped[int | None] = mapped_column(Integer)
    assists: Mapped[int | None] = mapped_column(Integer)
    points: Mapped[int | None] = mapped_column(Integer)


class PlayerTeamSeason(Base):
    __tablename__ = "player_team_seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("players.id"), index=True)
    team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"), index=True)
    season_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("seasons.id"), index=True)
    game_type: Mapped[int | None] = mapped_column(Integer, default=2)
    games_played: Mapped[int | None] = mapped_column(Integer)
    goals: Mapped[int | None] = mapped_column(Integer)
    assists: Mapped[int | None] = mapped_column(Integer)
    points: Mapped[int | None] = mapped_column(Integer)
