from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Award(Base):
    __tablename__ = "awards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str | None] = mapped_column(String(20))
    name: Mapped[str | None] = mapped_column(String(200), index=True)
    short_name: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(500))


class PlayerAward(Base):
    __tablename__ = "player_awards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id"), index=True
    )
    award_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("awards.id"), index=True
    )
    season_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("seasons.id"), index=True
    )
    team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"))
    is_finalist: Mapped[int | None] = mapped_column(Integer, default=0)
    rank: Mapped[int | None] = mapped_column(Integer)
    vote_pct: Mapped[int | None] = mapped_column(Integer)

    player: Mapped[Player | None] = relationship("Player")
    award: Mapped[Award | None] = relationship("Award")
    season: Mapped[Season | None] = relationship("Season")
    team: Mapped[Team | None] = relationship("Team")


from app.models.player import Player  # noqa: E402
from app.models.season import Season  # noqa: E402
from app.models.team import Team  # noqa: E402
