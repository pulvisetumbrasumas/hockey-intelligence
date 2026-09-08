from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id"), index=True
    )
    team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teams.id"), index=True
    )
    start_date: Mapped[datetime | None] = mapped_column(DateTime)
    end_date: Mapped[datetime | None] = mapped_column(DateTime)
    start_season_id: Mapped[int | None] = mapped_column(Integer)
    end_season_id: Mapped[int | None] = mapped_column(Integer)
    total_value: Mapped[float | None] = mapped_column(Float)
    avg_annual_value: Mapped[float | None] = mapped_column(Float)
    signing_bonus: Mapped[float | None] = mapped_column(Float)
    type: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str | None] = mapped_column(String(50))

    player: Mapped[Player | None] = relationship("Player")
    team: Mapped[Team | None] = relationship("Team")


from app.models.player import Player  # noqa: E402
from app.models.team import Team  # noqa: E402
