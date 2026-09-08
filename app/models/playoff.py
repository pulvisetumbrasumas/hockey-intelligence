from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class PlayoffSeries(Base):
    """Best-of-seven playoff series (authoritative history).

    Currently restores the conference finals from the 16-team playoff era
    (1993-94 onward). The Stanley Cup Final is sourced from the champions
    table; earlier rounds are pending restoration.
    """

    __tablename__ = "playoff_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("seasons.id"), index=True, nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    round_label: Mapped[str | None] = mapped_column(String(40), nullable=True)
    conference: Mapped[str | None] = mapped_column(String(20), nullable=True)
    winner_team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=True
    )
    winner_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    loser_team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=True
    )
    loser_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    winner_games: Mapped[int | None] = mapped_column(Integer, nullable=True)
    loser_games: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)

    def __repr__(self):
        return f"<PlayoffSeries(season={self.season_id}, round={self.round_number})>"
