from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Integer, String, Column, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.franchise import Franchise
    from app.models.season import Season


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    nhl_id: Mapped[Optional[int]] = mapped_column(Integer)
    franchise_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("franchises.id"), index=True
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(200))
    name: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    abbreviation: Mapped[Optional[str]] = mapped_column(String(10))
    tricode: Mapped[Optional[str]] = mapped_column(String(10))
    first_season_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    last_season_id: Mapped[Optional[int]] = mapped_column(Integer)
    active: Mapped[Optional[int]] = mapped_column(Integer, default=1)

    franchise: Mapped[Optional["Franchise"]] = relationship("Franchise")
    identities: Mapped[list["TeamIdentity"]] = relationship(
        "TeamIdentity", back_populates="team", order_by="TeamIdentity.start_year"
    )
    seasons: Mapped[list["TeamSeason"]] = relationship("TeamSeason", back_populates="team")

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.full_name}')>"


class TeamIdentity(Base):
    __tablename__ = "team_identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id"), index=True
    )
    franchise_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("franchises.id"), index=True
    )
    name: Mapped[Optional[str]] = mapped_column(String(200))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    abbr: Mapped[Optional[str]] = mapped_column(String(10))
    start_year: Mapped[Optional[int]] = mapped_column(Integer)
    end_year: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="identities")
    franchise: Mapped[Optional["Franchise"]] = relationship("Franchise")

    def __repr__(self):
        return f"<TeamIdentity(name='{self.name}', {self.start_year}-{self.end_year})>"


class TeamSeason(Base):
    __tablename__ = "team_seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id"), index=True
    )
    season_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("seasons.id"), index=True
    )
    games_played: Mapped[Optional[int]] = mapped_column(Integer)
    wins: Mapped[Optional[int]] = mapped_column(Integer)
    losses: Mapped[Optional[int]] = mapped_column(Integer)
    ot_losses: Mapped[Optional[int]] = mapped_column(Integer)
    ties: Mapped[Optional[int]] = mapped_column(Integer)
    points: Mapped[Optional[int]] = mapped_column(Integer)
    goals_for: Mapped[Optional[int]] = mapped_column(Integer)
    goals_against: Mapped[Optional[int]] = mapped_column(Integer)
    conference_rank: Mapped[Optional[int]] = mapped_column(Integer)
    division_rank: Mapped[Optional[int]] = mapped_column(Integer)
    playoffs_reached: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    stanley_cup: Mapped[Optional[int]] = mapped_column(Integer, default=0)

    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="seasons")
    season: Mapped[Optional["Season"]] = relationship("Season")

    def __repr__(self):
        return f"<TeamSeason(team={self.team_id}, season={self.season_id})>"