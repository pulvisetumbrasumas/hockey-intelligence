from sqlalchemy import Integer, String, Column, ForeignKey, Float, Index
from sqlalchemy.orm import relationship
from app.database.connection import Base


class TeamSeasonStats(Base):
    __tablename__ = "team_season_stats"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), index=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), index=True)
    game_type = Column(Integer, default=2)

    games_played = Column(Integer)
    wins = Column(Integer)
    losses = Column(Integer)
    ot_losses = Column(Integer)
    ties = Column(Integer)
    points = Column(Integer)
    goals_for = Column(Integer)
    goals_against = Column(Integer)
    power_play_pct = Column(Float)
    penalty_kill_pct = Column(Float)
    power_play_goals = Column(Integer)
    power_play_opportunities = Column(Integer)
    shorthanded_goals = Column(Integer)
    shorthanded_against = Column(Integer)
    shots_per_game = Column(Float)
    shots_against_per_game = Column(Float)
    faceoff_pct = Column(Float)
    hits = Column(Integer)
    blocked_shots = Column(Integer)
    takeaways = Column(Integer)
    giveaways = Column(Integer)
    penalty_minutes = Column(Float)

    team = relationship("Team")
    season = relationship("Season")

    def __repr__(self):
        return f"<TeamSeasonStats(team={self.team_id}, season={self.season_id})>"