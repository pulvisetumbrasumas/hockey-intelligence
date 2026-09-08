"""championship history: Stanley Cup winners & finalists per season

Revision ID: c1aa4e5f9d01
Revises: ae10f24c7b01
Create Date: 2026-09-08 16:30:00.000000

Sample data: authoritative historical results (1918-2026). The 2004-05 season
was cancelled by lockout; 2026-27 is in progress. Pre-1927 challenge-era
series totals are omitted where records are ambiguous.

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c1aa4e5f9d01'
down_revision: str | Sequence[str] | None = 'ae10f24c7b01'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (season_id, winner, runner_up, champ_wins, runner_wins, note)
CHAMPIONS: list[tuple[int, str | None, str | None, int | None, int | None, str | None]] = [
    (19171918, "Toronto Arenas", "Montreal Wanderers", None, None, "NHL title; Cup vs Vancouver Millionaires (PCHA)"),
    (19181919, "Montréal Canadiens", "Ottawa Senators (1917)", None, None, "Cup final vs Seattle Metropolitans abandoned (1919 flu); no Cup awarded"),
    (19191920, "Montréal Canadiens", "Seattle Metropolitans", 3, 2, "NHL playoff vs Ottawa 2–0; Cup decided in extra time"),
    (19201921, "Vancouver Millionaires", "Ottawa Senators (1917)", 3, 2, "NHL champion: Ottawa Senators"),
    (19211922, "Toronto St. Patricks", "Vancouver Millionaires", 3, 2, ""),
    (19221923, "Ottawa Senators (1917)", "Edmonton Eskimos", 2, 1, ""),
    (19231924, "Montréal Canadiens", "Calgary Tigers (WCHL)", 2, 0, ""),
    (19241925, "Victoria Cougars (WCL)", "Montréal Canadiens", 3, 1, "NHL champion: Montréal Canadiens"),
    (19251926, "Montreal Maroons", "Victoria Cougars (WCL)", 3, 1, ""),
    (19261927, "Ottawa Senators (1917)", "Boston Bruins", 2, 0, "First year of NHL-only Cup playoffs"),
    (19271928, "New York Rangers", "Montreal Maroons", 3, 2, ""),
    (19281929, "Boston Bruins", "New York Rangers", 2, 0, ""),
    (19291930, "Montréal Canadiens", "Boston Bruins", 2, 0, ""),
    (19301931, "Montréal Canadiens", "Chicago Blackhawks", 3, 2, ""),
    (19311932, "Toronto Maple Leafs", "New York Rangers", 3, 0, ""),
    (19321933, "New York Rangers", "Toronto Maple Leafs", 3, 1, ""),
    (19331934, "Chicago Blackhawks", "Detroit Red Wings", 3, 1, ""),
    (19341935, "Montreal Maroons", "Toronto Maple Leafs", 3, 0, ""),
    (19351936, "Detroit Red Wings", "Toronto Maple Leafs", 3, 1, ""),
    (19361937, "Detroit Red Wings", "New York Rangers", 3, 2, ""),
    (19371938, "Chicago Blackhawks", "Toronto Maple Leafs", 3, 1, ""),
    (19381939, "Boston Bruins", "Toronto Maple Leafs", 4, 1, ""),
    (19391940, "New York Rangers", "Toronto Maple Leafs", 4, 2, ""),
    (19401941, "Boston Bruins", "Detroit Red Wings", 4, 0, ""),
    (19411942, "Toronto Maple Leafs", "Detroit Red Wings", 4, 3, ""),
    (19421943, "Detroit Red Wings", "Boston Bruins", 4, 0, ""),
    (19431944, "Montréal Canadiens", "Chicago Blackhawks", 4, 0, ""),
    (19441945, "Toronto Maple Leafs", "Detroit Red Wings", 4, 3, ""),
    (19451946, "Montréal Canadiens", "Boston Bruins", 4, 1, ""),
    (19461947, "Toronto Maple Leafs", "Montréal Canadiens", 4, 2, ""),
    (19471948, "Toronto Maple Leafs", "Detroit Red Wings", 4, 0, ""),
    (19481949, "Toronto Maple Leafs", "Detroit Red Wings", 4, 0, ""),
    (19491950, "Detroit Red Wings", "New York Rangers", 4, 3, ""),
    (19501951, "Toronto Maple Leafs", "Montréal Canadiens", 4, 1, ""),
    (19511952, "Detroit Red Wings", "Montréal Canadiens", 4, 0, ""),
    (19521953, "Montréal Canadiens", "Boston Bruins", 4, 1, ""),
    (19531954, "Detroit Red Wings", "Montréal Canadiens", 4, 3, ""),
    (19541955, "Detroit Red Wings", "Montréal Canadiens", 4, 3, ""),
    (19551956, "Montréal Canadiens", "Detroit Red Wings", 4, 1, ""),
    (19561957, "Montréal Canadiens", "Boston Bruins", 4, 1, ""),
    (19571958, "Montréal Canadiens", "Boston Bruins", 4, 2, ""),
    (19581959, "Montréal Canadiens", "Toronto Maple Leafs", 4, 1, ""),
    (19591960, "Montréal Canadiens", "Toronto Maple Leafs", 4, 0, ""),
    (19601961, "Chicago Blackhawks", "Detroit Red Wings", 4, 2, ""),
    (19611962, "Toronto Maple Leafs", "Chicago Blackhawks", 4, 2, ""),
    (19621963, "Toronto Maple Leafs", "Detroit Red Wings", 4, 1, ""),
    (19631964, "Toronto Maple Leafs", "Detroit Red Wings", 4, 3, ""),
    (19641965, "Montréal Canadiens", "Chicago Blackhawks", 4, 3, ""),
    (19651966, "Montréal Canadiens", "Detroit Red Wings", 4, 2, ""),
    (19661967, "Toronto Maple Leafs", "Montréal Canadiens", 4, 2, ""),
    (19671968, "Montréal Canadiens", "St. Louis Blues", 4, 0, ""),
    (19681969, "Montréal Canadiens", "St. Louis Blues", 4, 0, ""),
    (19691970, "Boston Bruins", "St. Louis Blues", 4, 0, ""),
    (19701971, "Montréal Canadiens", "Chicago Blackhawks", 4, 3, ""),
    (19711972, "Boston Bruins", "New York Rangers", 4, 2, ""),
    (19721973, "Montréal Canadiens", "Chicago Blackhawks", 4, 2, ""),
    (19731974, "Philadelphia Flyers", "Boston Bruins", 4, 2, ""),
    (19741975, "Philadelphia Flyers", "Buffalo Sabres", 4, 2, ""),
    (19751976, "Montréal Canadiens", "Philadelphia Flyers", 4, 0, ""),
    (19761977, "Montréal Canadiens", "Boston Bruins", 4, 0, ""),
    (19771978, "Montréal Canadiens", "Boston Bruins", 4, 2, ""),
    (19781979, "Montréal Canadiens", "New York Rangers", 4, 1, ""),
    (19791980, "New York Islanders", "Philadelphia Flyers", 4, 2, ""),
    (19801981, "New York Islanders", "Minnesota North Stars", 4, 1, ""),
    (19811982, "New York Islanders", "Vancouver Canucks", 4, 0, ""),
    (19821983, "New York Islanders", "Edmonton Oilers", 4, 0, ""),
    (19831984, "Edmonton Oilers", "New York Islanders", 4, 1, ""),
    (19841985, "Edmonton Oilers", "Philadelphia Flyers", 4, 1, ""),
    (19851986, "Montréal Canadiens", "Calgary Flames", 4, 1, ""),
    (19861987, "Edmonton Oilers", "Philadelphia Flyers", 4, 3, ""),
    (19871988, "Edmonton Oilers", "Boston Bruins", 4, 0, ""),
    (19881989, "Calgary Flames", "Montréal Canadiens", 4, 2, ""),
    (19891990, "Edmonton Oilers", "Boston Bruins", 4, 1, ""),
    (19901991, "Pittsburgh Penguins", "Minnesota North Stars", 4, 2, ""),
    (19911992, "Pittsburgh Penguins", "Chicago Blackhawks", 4, 0, ""),
    (19921993, "Montréal Canadiens", "Los Angeles Kings", 4, 1, ""),
    (19931994, "New York Rangers", "Vancouver Canucks", 4, 3, ""),
    (19941995, "New Jersey Devils", "Detroit Red Wings", 4, 0, ""),
    (19951996, "Colorado Avalanche", "Florida Panthers", 4, 0, ""),
    (19961997, "Detroit Red Wings", "Philadelphia Flyers", 4, 0, ""),
    (19971998, "Detroit Red Wings", "Washington Capitals", 4, 0, ""),
    (19981999, "Dallas Stars", "Buffalo Sabres", 4, 2, ""),
    (19992000, "New Jersey Devils", "Dallas Stars", 4, 2, ""),
    (20002001, "Colorado Avalanche", "New Jersey Devils", 4, 3, ""),
    (20012002, "Detroit Red Wings", "Carolina Hurricanes", 4, 1, ""),
    (20022003, "New Jersey Devils", "Anaheim Ducks", 4, 3, "Mighty Ducks of Anaheim"),
    (20032004, "Tampa Bay Lightning", "Calgary Flames", 4, 3, ""),
    (20042005, None, None, None, None, "Lockout: season cancelled; no champion"),
    (20052006, "Carolina Hurricanes", "Edmonton Oilers", 4, 3, ""),
    (20062007, "Anaheim Ducks", "Ottawa Senators", 4, 1, ""),
    (20072008, "Detroit Red Wings", "Pittsburgh Penguins", 4, 2, ""),
    (20082009, "Pittsburgh Penguins", "Detroit Red Wings", 4, 3, ""),
    (20092010, "Chicago Blackhawks", "Philadelphia Flyers", 4, 2, ""),
    (20102011, "Boston Bruins", "Vancouver Canucks", 4, 3, ""),
    (20112012, "Los Angeles Kings", "New Jersey Devils", 4, 2, ""),
    (20122013, "Chicago Blackhawks", "Boston Bruins", 4, 2, ""),
    (20132014, "Los Angeles Kings", "New York Rangers", 4, 1, ""),
    (20142015, "Chicago Blackhawks", "Tampa Bay Lightning", 4, 2, ""),
    (20152016, "Pittsburgh Penguins", "San Jose Sharks", 4, 2, ""),
    (20162017, "Pittsburgh Penguins", "Nashville Predators", 4, 2, ""),
    (20172018, "Washington Capitals", "Vegas Golden Knights", 4, 1, ""),
    (20182019, "St. Louis Blues", "Boston Bruins", 4, 3, ""),
    (20192020, "Tampa Bay Lightning", "Dallas Stars", 4, 2, "Bubble playoffs in Edmonton/Toronto"),
    (20202021, "Tampa Bay Lightning", "Montréal Canadiens", 4, 1, ""),
    (20212022, "Colorado Avalanche", "Tampa Bay Lightning", 4, 2, ""),
    (20222023, "Vegas Golden Knights", "Florida Panthers", 4, 1, ""),
    (20232024, "Florida Panthers", "Edmonton Oilers", 4, 3, ""),
    (20242025, "Florida Panthers", "Edmonton Oilers", 4, 2, ""),
    (20252026, "Carolina Hurricanes", "Vegas Golden Knights", 4, 2, ""),
]


def upgrade() -> None:
    """Create champions table and seed championship history."""
    op.create_table(
        'champions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('winner_team_id', sa.Integer(), nullable=True),
        sa.Column('runner_team_id', sa.Integer(), nullable=True),
        sa.Column('winner_name', sa.String(length=120), nullable=True),
        sa.Column('runner_name', sa.String(length=120), nullable=True),
        sa.Column('champ_wins', sa.Integer(), nullable=True),
        sa.Column('runner_wins', sa.Integer(), nullable=True),
        sa.Column('note', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['runner_team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id']),
        sa.ForeignKeyConstraint(['winner_team_id'], ['teams.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('season_id'),
    )
    op.create_index(op.f('ix_champions_season_id'), 'champions', ['season_id'], unique=True)

    conn = op.get_bind()
    team_ids = {
        row[1]: row[0]
        for row in conn.execute(sa.text("SELECT id, full_name FROM teams")).fetchall()
    }
    rows: list[dict] = []
    for season_id, winner, runner, cw, rw, note in CHAMPIONS:
        rows.append(
            {
                "season_id": season_id,
                "winner_team_id": team_ids.get(winner),
                "runner_team_id": team_ids.get(runner),
                "winner_name": winner,
                "runner_name": runner,
                "champ_wins": cw,
                "runner_wins": rw,
                "note": note,
            }
        )
    conn.execute(sa.table(
        'champions',
        sa.column('season_id', sa.Integer()),
        sa.column('winner_team_id', sa.Integer()),
        sa.column('runner_team_id', sa.Integer()),
        sa.column('winner_name', sa.String()),
        sa.column('runner_name', sa.String()),
        sa.column('champ_wins', sa.Integer()),
        sa.column('runner_wins', sa.Integer()),
        sa.column('note', sa.String()),
    ).insert().values(rows))


def downgrade() -> None:
    op.drop_index(op.f('ix_champions_season_id'), table_name='champions')
    op.drop_table('champions')
