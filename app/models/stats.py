from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Integer, String, Column, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.player import Player
    from app.models.season import Season


class PlayerSeasonStats(Base):
    __tablename__ = "player_season_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), index=True
    )
    season_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("seasons.id"), index=True
    )
    team_abbrevs: Mapped[Optional[str]] = mapped_column(String(50))
    game_type: Mapped[Optional[int]] = mapped_column(Integer, default=2)

    games_played: Mapped[Optional[int]] = mapped_column(Integer)
    goals: Mapped[Optional[int]] = mapped_column(Integer)
    assists: Mapped[Optional[int]] = mapped_column(Integer)
    points: Mapped[Optional[int]] = mapped_column(Integer)
    points_per_game: Mapped[Optional[float]] = mapped_column(Float)
    plus_minus: Mapped[Optional[int]] = mapped_column(Integer)
    penalty_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    ev_goals: Mapped[Optional[int]] = mapped_column(Integer)
    ev_points: Mapped[Optional[int]] = mapped_column(Integer)
    pp_goals: Mapped[Optional[int]] = mapped_column(Integer)
    pp_points: Mapped[Optional[int]] = mapped_column(Integer)
    sh_goals: Mapped[Optional[int]] = mapped_column(Integer)
    sh_points: Mapped[Optional[int]] = mapped_column(Integer)
    game_winning_goals: Mapped[Optional[int]] = mapped_column(Integer)
    ot_goals: Mapped[Optional[int]] = mapped_column(Integer)
    shots: Mapped[Optional[int]] = mapped_column(Integer)
    shooting_pct: Mapped[Optional[float]] = mapped_column(Float)
    faceoff_win_pct: Mapped[Optional[float]] = mapped_column(Float)
    time_on_ice_per_game: Mapped[Optional[float]] = mapped_column(Float)
    shifts_per_game: Mapped[Optional[float]] = mapped_column(Float)
    hits: Mapped[Optional[int]] = mapped_column(Integer)
    blocked_shots: Mapped[Optional[int]] = mapped_column(Integer)
    takeaways: Mapped[Optional[int]] = mapped_column(Integer)
    giveaways: Mapped[Optional[int]] = mapped_column(Integer)

    wins: Mapped[Optional[int]] = mapped_column(Integer)
    losses: Mapped[Optional[int]] = mapped_column(Integer)
    ot_losses: Mapped[Optional[int]] = mapped_column(Integer)
    ties: Mapped[Optional[int]] = mapped_column(Integer)
    goals_against: Mapped[Optional[int]] = mapped_column(Integer)
    shots_against: Mapped[Optional[int]] = mapped_column(Integer)
    saves: Mapped[Optional[int]] = mapped_column(Integer)
    save_pct: Mapped[Optional[float]] = mapped_column(Float)
    goals_against_average: Mapped[Optional[float]] = mapped_column(Float)
    shutouts: Mapped[Optional[int]] = mapped_column(Integer)
    games_started: Mapped[Optional[int]] = mapped_column(Integer)
    time_on_ice: Mapped[Optional[int]] = mapped_column(Integer)
    is_goalie: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    goalie_stats: Mapped[Optional[int]] = mapped_column(Integer, default=0)

    player: Mapped[Optional["Player"]] = relationship("Player", back_populates="season_stats")
    season: Mapped[Optional["Season"]] = relationship("Season")

    def __repr__(self):
        return f"<PlayerSeasonStats(player={self.player_id}, season={self.season_id})>"


class GoalieSeasonStats(Base):
    __tablename__ = "goalie_season_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), index=True
    )
    season_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("seasons.id"), index=True
    )
    team_abbrevs: Mapped[Optional[str]] = mapped_column(String(50))
    game_type: Mapped[Optional[int]] = mapped_column(Integer, default=2)

    games_played: Mapped[Optional[int]] = mapped_column(Integer)
    games_started: Mapped[Optional[int]] = mapped_column(Integer)
    wins: Mapped[Optional[int]] = mapped_column(Integer)
    losses: Mapped[Optional[int]] = mapped_column(Integer)
    ot_losses: Mapped[Optional[int]] = mapped_column(Integer)
    ties: Mapped[Optional[int]] = mapped_column(Integer)
    goals_against: Mapped[Optional[int]] = mapped_column(Integer)
    shots_against: Mapped[Optional[int]] = mapped_column(Integer)
    saves: Mapped[Optional[int]] = mapped_column(Integer)
    save_pct: Mapped[Optional[float]] = mapped_column(Float)
    goals_against_average: Mapped[Optional[float]] = mapped_column(Float)
    shutouts: Mapped[Optional[int]] = mapped_column(Integer)
    time_on_ice: Mapped[Optional[int]] = mapped_column(Integer)
    goals: Mapped[Optional[int]] = mapped_column(Integer)
    assists: Mapped[Optional[int]] = mapped_column(Integer)
    points: Mapped[Optional[int]] = mapped_column(Integer)
    penalty_minutes: Mapped[Optional[int]] = mapped_column(Integer)

    player: Mapped[Optional["Player"]] = relationship("Player", back_populates="goalie_stats")
    season: Mapped[Optional["Season"]] = relationship("Season")

    def __repr__(self):
        return f"<GoalieSeasonStats(player={self.player_id}, season={self.season_id})>"