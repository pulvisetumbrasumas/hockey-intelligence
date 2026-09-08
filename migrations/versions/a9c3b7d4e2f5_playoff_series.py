"""playoff series: conference finals history (1994-2026)

Revision ID: a9c3b7d4e2f5
Revises: d3b2f6a8c51e
Create Date: 2026-09-08 18:00:00.000000

Seeds the Eastern and Western Conference Finals from the 16-team playoff era
(1993-94 through 2025-26) as authoritative reference data. The Stanley Cup
Final itself lives in the champions table; earlier rounds are pending
restoration. The 2004-05 season was cancelled by lockout.

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a9c3b7d4e2f5'
down_revision: str | Sequence[str] | None = 'd3b2f6a8c51e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (season_id, conference, winner, loser, winner_games, loser_games)
CONFERENCE_FINALS: list[tuple[int, str, str, str, int, int]] = [
    (19931994, "Eastern", "New York Rangers", "New Jersey Devils", 4, 3),
    (19931994, "Western", "Vancouver Canucks", "Toronto Maple Leafs", 4, 1),
    (19941995, "Eastern", "New Jersey Devils", "Philadelphia Flyers", 4, 2),
    (19941995, "Western", "Detroit Red Wings", "Chicago Blackhawks", 4, 1),
    (19951996, "Eastern", "Florida Panthers", "Pittsburgh Penguins", 4, 3),
    (19951996, "Western", "Colorado Avalanche", "Detroit Red Wings", 4, 2),
    (19961997, "Eastern", "Philadelphia Flyers", "New York Rangers", 4, 1),
    (19961997, "Western", "Detroit Red Wings", "Colorado Avalanche", 4, 2),
    (19971998, "Eastern", "Washington Capitals", "Buffalo Sabres", 4, 2),
    (19971998, "Western", "Detroit Red Wings", "Dallas Stars", 4, 2),
    (19981999, "Eastern", "Buffalo Sabres", "Toronto Maple Leafs", 4, 1),
    (19981999, "Western", "Dallas Stars", "Colorado Avalanche", 4, 3),
    (19992000, "Eastern", "New Jersey Devils", "Philadelphia Flyers", 4, 3),
    (19992000, "Western", "Dallas Stars", "Colorado Avalanche", 4, 3),
    (20002001, "Eastern", "New Jersey Devils", "Boston Bruins", 4, 2),
    (20002001, "Western", "Colorado Avalanche", "St. Louis Blues", 4, 1),
    (20012002, "Eastern", "Carolina Hurricanes", "Toronto Maple Leafs", 4, 2),
    (20012002, "Western", "Detroit Red Wings", "Colorado Avalanche", 4, 3),
    (20022003, "Eastern", "New Jersey Devils", "Ottawa Senators", 4, 3),
    (20022003, "Western", "Anaheim Ducks", "Minnesota Wild", 4, 0),
    (20032004, "Eastern", "Tampa Bay Lightning", "Philadelphia Flyers", 4, 3),
    (20032004, "Western", "Calgary Flames", "San Jose Sharks", 4, 2),
    (20052006, "Eastern", "Carolina Hurricanes", "Buffalo Sabres", 4, 3),
    (20052006, "Western", "Edmonton Oilers", "Anaheim Ducks", 4, 1),
    (20062007, "Eastern", "Ottawa Senators", "Buffalo Sabres", 4, 1),
    (20062007, "Western", "Anaheim Ducks", "Detroit Red Wings", 4, 2),
    (20072008, "Eastern", "Pittsburgh Penguins", "Philadelphia Flyers", 4, 1),
    (20072008, "Western", "Detroit Red Wings", "Dallas Stars", 4, 2),
    (20082009, "Eastern", "Pittsburgh Penguins", "Carolina Hurricanes", 4, 0),
    (20082009, "Western", "Detroit Red Wings", "Chicago Blackhawks", 4, 1),
    (20092010, "Eastern", "Philadelphia Flyers", "Montréal Canadiens", 4, 1),
    (20092010, "Western", "Chicago Blackhawks", "San Jose Sharks", 4, 0),
    (20102011, "Eastern", "Boston Bruins", "Tampa Bay Lightning", 4, 3),
    (20102011, "Western", "Vancouver Canucks", "San Jose Sharks", 4, 1),
    (20112012, "Eastern", "New Jersey Devils", "New York Rangers", 4, 2),
    (20112012, "Western", "Los Angeles Kings", "Phoenix Coyotes", 4, 1),
    (20122013, "Eastern", "Boston Bruins", "Pittsburgh Penguins", 4, 0),
    (20122013, "Western", "Chicago Blackhawks", "Los Angeles Kings", 4, 1),
    (20132014, "Eastern", "New York Rangers", "Montréal Canadiens", 4, 2),
    (20132014, "Western", "Los Angeles Kings", "Chicago Blackhawks", 4, 3),
    (20142015, "Eastern", "Tampa Bay Lightning", "New York Rangers", 4, 3),
    (20142015, "Western", "Chicago Blackhawks", "Anaheim Ducks", 4, 3),
    (20152016, "Eastern", "Pittsburgh Penguins", "Tampa Bay Lightning", 4, 3),
    (20152016, "Western", "San Jose Sharks", "St. Louis Blues", 4, 2),
    (20162017, "Eastern", "Pittsburgh Penguins", "Ottawa Senators", 4, 3),
    (20162017, "Western", "Nashville Predators", "Anaheim Ducks", 4, 2),
    (20172018, "Eastern", "Washington Capitals", "Tampa Bay Lightning", 4, 3),
    (20172018, "Western", "Vegas Golden Knights", "Winnipeg Jets", 4, 1),
    (20182019, "Eastern", "Boston Bruins", "Carolina Hurricanes", 4, 0),
    (20182019, "Western", "St. Louis Blues", "San Jose Sharks", 4, 2),
    (20192020, "Eastern", "Tampa Bay Lightning", "New York Islanders", 4, 2),
    (20192020, "Western", "Dallas Stars", "Vegas Golden Knights", 4, 1),
    (20202021, "Eastern", "Tampa Bay Lightning", "New York Islanders", 4, 3),
    (20202021, "Western", "Montréal Canadiens", "Vegas Golden Knights", 4, 2),
    (20212022, "Eastern", "Tampa Bay Lightning", "New York Rangers", 4, 2),
    (20212022, "Western", "Colorado Avalanche", "Edmonton Oilers", 4, 0),
    (20222023, "Eastern", "Florida Panthers", "Carolina Hurricanes", 4, 0),
    (20222023, "Western", "Vegas Golden Knights", "Dallas Stars", 4, 2),
    (20232024, "Eastern", "Florida Panthers", "New York Rangers", 4, 2),
    (20232024, "Western", "Edmonton Oilers", "Dallas Stars", 4, 2),
    (20242025, "Eastern", "Florida Panthers", "Carolina Hurricanes", 4, 1),
    (20242025, "Western", "Edmonton Oilers", "Dallas Stars", 4, 1),
    (20252026, "Eastern", "Carolina Hurricanes", "Montréal Canadiens", 4, 1),
    (20252026, "Western", "Vegas Golden Knights", "Colorado Avalanche", 4, 0),
]


def upgrade() -> None:
    """Create playoff_series table and seed conference finals."""
    op.create_table(
        'playoff_series',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('round_label', sa.String(length=40), nullable=True),
        sa.Column('conference', sa.String(length=20), nullable=True),
        sa.Column('winner_team_id', sa.Integer(), nullable=True),
        sa.Column('winner_name', sa.String(length=120), nullable=True),
        sa.Column('loser_team_id', sa.Integer(), nullable=True),
        sa.Column('loser_name', sa.String(length=120), nullable=True),
        sa.Column('winner_games', sa.Integer(), nullable=True),
        sa.Column('loser_games', sa.Integer(), nullable=True),
        sa.Column('note', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['loser_team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id']),
        sa.ForeignKeyConstraint(['winner_team_id'], ['teams.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_playoff_series_season_id'), 'playoff_series', ['season_id'], unique=False
    )

    conn = op.get_bind()
    team_ids = {
        row[1]: row[0]
        for row in conn.execute(sa.text("SELECT id, full_name FROM teams")).fetchall()
    }
    rows: list[dict] = []
    for season_id, conference, winner, loser, wg, lg in CONFERENCE_FINALS:
        rows.append(
            {
                "season_id": season_id,
                "round_number": 3,
                "round_label": "Conference Final",
                "conference": conference,
                "winner_team_id": team_ids.get(winner),
                "winner_name": winner,
                "loser_team_id": team_ids.get(loser),
                "loser_name": loser,
                "winner_games": wg,
                "loser_games": lg,
                "note": None,
            }
        )
    conn.execute(sa.table(
        'playoff_series',
        sa.column('season_id', sa.Integer()),
        sa.column('round_number', sa.Integer()),
        sa.column('round_label', sa.String()),
        sa.column('conference', sa.String()),
        sa.column('winner_team_id', sa.Integer()),
        sa.column('winner_name', sa.String()),
        sa.column('loser_team_id', sa.Integer()),
        sa.column('loser_name', sa.String()),
        sa.column('winner_games', sa.Integer()),
        sa.column('loser_games', sa.Integer()),
        sa.column('note', sa.String()),
    ).insert().values(rows))


def downgrade() -> None:
    op.drop_index(op.f('ix_playoff_series_season_id'), table_name='playoff_series')
    op.drop_table('playoff_series')
