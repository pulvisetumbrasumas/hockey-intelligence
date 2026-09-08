from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base


class DraftPick(Base):
    __tablename__ = "draft_picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("seasons.id"), index=True
    )
    round: Mapped[Optional[int]] = mapped_column(Integer)
    pick_number: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id"), index=True
    )
    player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), index=True
    )
    player_name: Mapped[Optional[str]] = mapped_column(String(200))
    position: Mapped[Optional[str]] = mapped_column(String(5))
    minor_league_team: Mapped[Optional[str]] = mapped_column(String(200))
    from_team_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"))
    nhlnail_points: Mapped[Optional[int]] = mapped_column(Integer)

    team: Mapped[Optional["Team"]] = relationship("Team", foreign_keys=[team_id])
    player: Mapped[Optional["Player"]] = relationship("Player")


from app.models.player import Player  # noqa: E402
from app.models.team import Team  # noqa: E402