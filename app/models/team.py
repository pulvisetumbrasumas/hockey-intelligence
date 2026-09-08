from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.franchise import Franchise
    from app.models.season import Season


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    nhl_id: Mapped[int | None] = mapped_column(Integer)
    franchise_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("franchises.id"), index=True
    )
    full_name: Mapped[str | None] = mapped_column(String(200))
    name: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    abbreviation: Mapped[str | None] = mapped_column(String(10))
    tricode: Mapped[str | None] = mapped_column(String(10))
    first_season_id: Mapped[int | None] = mapped_column(Integer, index=True)
    last_season_id: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[int | None] = mapped_column(Integer, default=1)

    franchise: Mapped[Franchise | None] = relationship("Franchise")
    identities: Mapped[list[TeamIdentity]] = relationship(
        "TeamIdentity", back_populates="team", order_by="TeamIdentity.start_year"
    )
    seasons: Mapped[list[TeamSeason]] = relationship("TeamSeason", back_populates="team")

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.full_name}')>"


class TeamIdentity(Base):
    __tablename__ = "team_identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teams.id"), index=True
    )
    franchise_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("franchises.id"), index=True
    )
    name: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(100))
    abbr: Mapped[str | None] = mapped_column(String(10))
    start_year: Mapped[int | None] = mapped_column(Integer)
    end_year: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    team: Mapped[Team | None] = relationship("Team", back_populates="identities")
    franchise: Mapped[Franchise | None] = relationship("Franchise")

    def __repr__(self):
        return f"<TeamIdentity(name='{self.name}', {self.start_year}-{self.end_year})>"


class TeamSeason(Base):
    __tablename__ = "team_seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teams.id"), index=True
    )
    season_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("seasons.id"), index=True
    )
    games_played: Mapped[int | None] = mapped_column(Integer)
    wins: Mapped[int | None] = mapped_column(Integer)
    losses: Mapped[int | None] = mapped_column(Integer)
    ot_losses: Mapped[int | None] = mapped_column(Integer)
    ties: Mapped[int | None] = mapped_column(Integer)
    points: Mapped[int | None] = mapped_column(Integer)
    goals_for: Mapped[int | None] = mapped_column(Integer)
    goals_against: Mapped[int | None] = mapped_column(Integer)
    conference_rank: Mapped[int | None] = mapped_column(Integer)
    division_rank: Mapped[int | None] = mapped_column(Integer)
    playoffs_reached: Mapped[int | None] = mapped_column(Integer, default=0)
    stanley_cup: Mapped[int | None] = mapped_column(Integer, default=0)

    team: Mapped[Team | None] = relationship("Team", back_populates="seasons")
    season: Mapped[Season | None] = relationship("Season")

    def __repr__(self):
        return f"<TeamSeason(team={self.team_id}, season={self.season_id})>"
