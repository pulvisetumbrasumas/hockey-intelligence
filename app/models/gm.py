from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base


class GeneralManager(Base):
    __tablename__ = "general_managers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    active: Mapped[Optional[int]] = mapped_column(Integer, default=1)


class TeamGM(Base):
    __tablename__ = "team_gms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gm_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("general_managers.id"), index=True
    )
    team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id"), index=True
    )
    start_year: Mapped[Optional[int]] = mapped_column(Integer)
    end_year: Mapped[Optional[int]] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String(100))

    gm: Mapped[Optional["GeneralManager"]] = relationship("GeneralManager")
    team: Mapped[Optional["Team"]] = relationship("Team")


from app.models.team import Team  # noqa: E402