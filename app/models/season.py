from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    formatted_id: Mapped[str | None] = mapped_column(String(10))
    start_date: Mapped[datetime | None] = mapped_column(DateTime)
    regular_season_end_date: Mapped[datetime | None] = mapped_column(DateTime)
    end_date: Mapped[datetime | None] = mapped_column(DateTime)
    regular_season_games: Mapped[int | None] = mapped_column(Integer)
    total_regular_season_games: Mapped[int | None] = mapped_column(Integer)
    total_playoff_games: Mapped[int | None] = mapped_column(Integer)
    number_of_teams: Mapped[int | None] = mapped_column(Integer)
    season_ordinal: Mapped[int | None] = mapped_column(Integer)
    ties_used: Mapped[int | None] = mapped_column(Integer)
    ot_loss_point: Mapped[int | None] = mapped_column(Integer, default=0)
    wildcard_used: Mapped[int | None] = mapped_column(Integer, default=0)

    def __repr__(self):
        return f"<Season(id={self.id}, formatted='{self.formatted_id}')>"
