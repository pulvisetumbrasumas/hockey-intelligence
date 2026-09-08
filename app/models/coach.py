from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base


class Coach(Base):
    __tablename__ = "coaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    is_goalie_coach: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    is_assistant: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    active: Mapped[Optional[int]] = mapped_column(Integer, default=1)


class TeamCoach(Base):
    __tablename__ = "team_coaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coach_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("coaches.id"), index=True
    )
    team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id"), index=True
    )
    season_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("seasons.id"), index=True
    )
    start_year: Mapped[Optional[int]] = mapped_column(Integer)
    end_year: Mapped[Optional[int]] = mapped_column(Integer)
    games: Mapped[Optional[int]] = mapped_column(Integer)
    wins: Mapped[Optional[int]] = mapped_column(Integer)
    losses: Mapped[Optional[int]] = mapped_column(Integer)
    ot_losses: Mapped[Optional[int]] = mapped_column(Integer)
    points: Mapped[Optional[int]] = mapped_column(Integer)
    playoff_games: Mapped[Optional[int]] = mapped_column(Integer)
    playoff_wins: Mapped[Optional[int]] = mapped_column(Integer)

    coach: Mapped[Optional["Coach"]] = relationship("Coach")
    team: Mapped[Optional["Team"]] = relationship("Team")
    season: Mapped[Optional["Season"]] = relationship("Season")


from app.models.season import Season  # noqa: E402
from app.models.team import Team  # noqa: E402