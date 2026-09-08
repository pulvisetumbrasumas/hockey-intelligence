from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Column, ForeignKey, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), index=True
    )
    team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id"), index=True
    )
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    start_season_id: Mapped[Optional[int]] = mapped_column(Integer)
    end_season_id: Mapped[Optional[int]] = mapped_column(Integer)
    total_value: Mapped[Optional[float]] = mapped_column(Float)
    avg_annual_value: Mapped[Optional[float]] = mapped_column(Float)
    signing_bonus: Mapped[Optional[float]] = mapped_column(Float)
    type: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[Optional[str]] = mapped_column(String(50))

    player: Mapped[Optional["Player"]] = relationship("Player")
    team: Mapped[Optional["Team"]] = relationship("Team")


from app.models.player import Player  # noqa: E402
from app.models.team import Team  # noqa: E402