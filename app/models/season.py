from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, ForeignKey, DateTime, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    formatted_id: Mapped[Optional[str]] = mapped_column(String(10))
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    regular_season_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    regular_season_games: Mapped[Optional[int]] = mapped_column(Integer)
    total_regular_season_games: Mapped[Optional[int]] = mapped_column(Integer)
    total_playoff_games: Mapped[Optional[int]] = mapped_column(Integer)
    number_of_teams: Mapped[Optional[int]] = mapped_column(Integer)
    season_ordinal: Mapped[Optional[int]] = mapped_column(Integer)
    ties_used: Mapped[Optional[int]] = mapped_column(Integer)
    ot_loss_point: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    wildcard_used: Mapped[Optional[int]] = mapped_column(Integer, default=0)

    def __repr__(self):
        return f"<Season(id={self.id}, formatted='{self.formatted_id}')>"