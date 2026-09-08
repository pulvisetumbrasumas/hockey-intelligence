from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Integer, String, Column, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.stats import GoalieSeasonStats, PlayerSeasonStats


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    nhl_id: Mapped[Optional[int]] = mapped_column(Integer)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    position_code: Mapped[Optional[str]] = mapped_column(String(5), index=True)
    primary_position: Mapped[Optional[str]] = mapped_column(String(50))
    birth_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    birth_city: Mapped[Optional[str]] = mapped_column(String(100))
    birth_country: Mapped[Optional[str]] = mapped_column(String(100))
    height: Mapped[Optional[str]] = mapped_column(String(20))
    weight: Mapped[Optional[int]] = mapped_column(Integer)
    shoots_catches: Mapped[Optional[str]] = mapped_column(String(1))
    is_goalie: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    is_rookie: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    draft_year: Mapped[Optional[int]] = mapped_column(Integer)
    draft_round: Mapped[Optional[int]] = mapped_column(Integer)
    draft_overall: Mapped[Optional[int]] = mapped_column(Integer)
    draft_team: Mapped[Optional[str]] = mapped_column(String(100))
    active: Mapped[Optional[int]] = mapped_column(Integer, default=1)

    season_stats: Mapped[list["PlayerSeasonStats"]] = relationship(
        back_populates="player",
    )
    goalie_stats: Mapped[list["GoalieSeasonStats"]] = relationship(
        back_populates="player",
    )

    def __repr__(self):
        return f"<Player(id={self.id}, name='{self.full_name}')>"


class PlayerPosition(Base):
    __tablename__ = "player_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("players.id"), index=True)
    position: Mapped[Optional[str]] = mapped_column(String(50))
    seasons: Mapped[Optional[str]] = mapped_column(String(50))
    games: Mapped[Optional[int]] = mapped_column(Integer)
    goals: Mapped[Optional[int]] = mapped_column(Integer)
    assists: Mapped[Optional[int]] = mapped_column(Integer)
    points: Mapped[Optional[int]] = mapped_column(Integer)


class PlayerTeamSeason(Base):
    __tablename__ = "player_team_seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("players.id"), index=True)
    team_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"), index=True)
    season_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("seasons.id"), index=True)
    game_type: Mapped[Optional[int]] = mapped_column(Integer, default=2)
    games_played: Mapped[Optional[int]] = mapped_column(Integer)
    goals: Mapped[Optional[int]] = mapped_column(Integer)
    assists: Mapped[Optional[int]] = mapped_column(Integer)
    points: Mapped[Optional[int]] = mapped_column(Integer)