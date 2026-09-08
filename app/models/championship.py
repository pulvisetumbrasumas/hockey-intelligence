from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Champion(Base):
    """Stanley Cup champion and finalist per season (authoritative history)."""

    __tablename__ = "champions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("seasons.id"), unique=True, nullable=False
    )
    winner_team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=True
    )
    runner_team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=True
    )
    winner_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    runner_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    champ_wins: Mapped[int | None] = mapped_column(Integer, nullable=True)
    runner_wins: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)

    def __repr__(self):
        return f"<Champion(season={self.season_id}, winner={self.winner_name})>"
