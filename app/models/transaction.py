from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    type: Mapped[str | None] = mapped_column(String(50), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teams.id"), index=True
    )
    player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id"), index=True
    )
    from_team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"))
    to_team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"))
    season_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("seasons.id"), index=True
    )
    details: Mapped[str | None] = mapped_column(Text)

    player: Mapped[Player | None] = relationship("Player")
    team: Mapped[Team | None] = relationship("Team", foreign_keys=[team_id])
    from_team: Mapped[Team | None] = relationship("Team", foreign_keys=[from_team_id])
    to_team: Mapped[Team | None] = relationship("Team", foreign_keys=[to_team_id])


from app.models.player import Player  # noqa: E402
from app.models.team import Team  # noqa: E402
