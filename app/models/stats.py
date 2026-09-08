from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.player import Player
    from app.models.season import Season


class PlayerSeasonStats(Base):
    __tablename__ = "player_season_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id"), index=True
    )
    season_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("seasons.id"), index=True
    )
    team_abbrevs: Mapped[str | None] = mapped_column(String(50))
    game_type: Mapped[int | None] = mapped_column(Integer, default=2)

    games_played: Mapped[int | None] = mapped_column(Integer)
    goals: Mapped[int | None] = mapped_column(Integer)
    assists: Mapped[int | None] = mapped_column(Integer)
    points: Mapped[int | None] = mapped_column(Integer)
    points_per_game: Mapped[float | None] = mapped_column(Float)
    plus_minus: Mapped[int | None] = mapped_column(Integer)
    penalty_minutes: Mapped[int | None] = mapped_column(Integer)
    ev_goals: Mapped[int | None] = mapped_column(Integer)
    ev_points: Mapped[int | None] = mapped_column(Integer)
    pp_goals: Mapped[int | None] = mapped_column(Integer)
    pp_points: Mapped[int | None] = mapped_column(Integer)
    sh_goals: Mapped[int | None] = mapped_column(Integer)
    sh_points: Mapped[int | None] = mapped_column(Integer)
    game_winning_goals: Mapped[int | None] = mapped_column(Integer)
    ot_goals: Mapped[int | None] = mapped_column(Integer)
    shots: Mapped[int | None] = mapped_column(Integer)
    shooting_pct: Mapped[float | None] = mapped_column(Float)
    faceoff_win_pct: Mapped[float | None] = mapped_column(Float)
    time_on_ice_per_game: Mapped[float | None] = mapped_column(Float)
    shifts_per_game: Mapped[float | None] = mapped_column(Float)
    hits: Mapped[int | None] = mapped_column(Integer)
    blocked_shots: Mapped[int | None] = mapped_column(Integer)
    takeaways: Mapped[int | None] = mapped_column(Integer)
    giveaways: Mapped[int | None] = mapped_column(Integer)

    wins: Mapped[int | None] = mapped_column(Integer)
    losses: Mapped[int | None] = mapped_column(Integer)
    ot_losses: Mapped[int | None] = mapped_column(Integer)
    ties: Mapped[int | None] = mapped_column(Integer)
    goals_against: Mapped[int | None] = mapped_column(Integer)
    shots_against: Mapped[int | None] = mapped_column(Integer)
    saves: Mapped[int | None] = mapped_column(Integer)
    save_pct: Mapped[float | None] = mapped_column(Float)
    goals_against_average: Mapped[float | None] = mapped_column(Float)
    shutouts: Mapped[int | None] = mapped_column(Integer)
    games_started: Mapped[int | None] = mapped_column(Integer)
    time_on_ice: Mapped[int | None] = mapped_column(Integer)
    is_goalie: Mapped[int | None] = mapped_column(Integer, default=0)
    goalie_stats: Mapped[int | None] = mapped_column(Integer, default=0)

    player: Mapped[Player | None] = relationship("Player", back_populates="season_stats")
    season: Mapped[Season | None] = relationship("Season")

    def __repr__(self):
        return f"<PlayerSeasonStats(player={self.player_id}, season={self.season_id})>"


class GoalieSeasonStats(Base):
    __tablename__ = "goalie_season_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id"), index=True
    )
    season_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("seasons.id"), index=True
    )
    team_abbrevs: Mapped[str | None] = mapped_column(String(50))
    game_type: Mapped[int | None] = mapped_column(Integer, default=2)

    games_played: Mapped[int | None] = mapped_column(Integer)
    games_started: Mapped[int | None] = mapped_column(Integer)
    wins: Mapped[int | None] = mapped_column(Integer)
    losses: Mapped[int | None] = mapped_column(Integer)
    ot_losses: Mapped[int | None] = mapped_column(Integer)
    ties: Mapped[int | None] = mapped_column(Integer)
    goals_against: Mapped[int | None] = mapped_column(Integer)
    shots_against: Mapped[int | None] = mapped_column(Integer)
    saves: Mapped[int | None] = mapped_column(Integer)
    save_pct: Mapped[float | None] = mapped_column(Float)
    goals_against_average: Mapped[float | None] = mapped_column(Float)
    shutouts: Mapped[int | None] = mapped_column(Integer)
    time_on_ice: Mapped[int | None] = mapped_column(Integer)
    goals: Mapped[int | None] = mapped_column(Integer)
    assists: Mapped[int | None] = mapped_column(Integer)
    points: Mapped[int | None] = mapped_column(Integer)
    penalty_minutes: Mapped[int | None] = mapped_column(Integer)

    player: Mapped[Player | None] = relationship("Player", back_populates="goalie_stats")
    season: Mapped[Season | None] = relationship("Season")

    def __repr__(self):
        return f"<GoalieSeasonStats(player={self.player_id}, season={self.season_id})>"
