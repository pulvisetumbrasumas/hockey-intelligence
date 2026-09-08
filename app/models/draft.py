from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class DraftPick(Base):
    __tablename__ = "draft_picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("seasons.id"), index=True
    )
    round: Mapped[int | None] = mapped_column(Integer)
    pick_number: Mapped[int | None] = mapped_column(Integer, index=True)
    team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teams.id"), index=True
    )
    player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id"), index=True
    )
    player_name: Mapped[str | None] = mapped_column(String(200))
    position: Mapped[str | None] = mapped_column(String(5))
    minor_league_team: Mapped[str | None] = mapped_column(String(200))
    from_team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"))
    nhlnail_points: Mapped[int | None] = mapped_column(Integer)

    team: Mapped[Team | None] = relationship("Team", foreign_keys=[team_id])
    player: Mapped[Player | None] = relationship("Player")


from app.models.player import Player  # noqa: E402
from app.models.team import Team  # noqa: E402
