"""teams: conference & division columns (current alignment)

Revision ID: d3b2f6a8c51e
Revises: c1aa4e5f9d01
Create Date: 2026-09-08 17:15:00.000000

Backfills the 32 current NHL clubs with their conference/division as of the
2013-14 alignment (stable through today). Older era standings therefore report
league splits only; the standings route falls back with a note.

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd3b2f6a8c51e'
down_revision: str | Sequence[str] | None = 'c1aa4e5f9d01'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# abbreviation -> (conference, division)
ALIGNMENT: dict[str, tuple[str, str]] = {
    "MTL": ("Eastern", "Atlantic"), "BOS": ("Eastern", "Atlantic"),
    "BUF": ("Eastern", "Atlantic"), "DET": ("Eastern", "Atlantic"),
    "FLA": ("Eastern", "Atlantic"), "OTT": ("Eastern", "Atlantic"),
    "TBL": ("Eastern", "Atlantic"), "TOR": ("Eastern", "Atlantic"),
    "CAR": ("Eastern", "Metropolitan"), "CBJ": ("Eastern", "Metropolitan"),
    "NJD": ("Eastern", "Metropolitan"), "NYI": ("Eastern", "Metropolitan"),
    "NYR": ("Eastern", "Metropolitan"), "PHI": ("Eastern", "Metropolitan"),
    "PIT": ("Eastern", "Metropolitan"), "WSH": ("Eastern", "Metropolitan"),
    "CHI": ("Western", "Central"), "COL": ("Western", "Central"),
    "DAL": ("Western", "Central"), "MIN": ("Western", "Central"),
    "NSH": ("Western", "Central"), "STL": ("Western", "Central"),
    "UTA": ("Western", "Central"), "WPG": ("Western", "Central"),
    "ANA": ("Western", "Pacific"), "CGY": ("Western", "Pacific"),
    "EDM": ("Western", "Pacific"), "LAK": ("Western", "Pacific"),
    "SEA": ("Western", "Pacific"), "SJS": ("Western", "Pacific"),
    "VAN": ("Western", "Pacific"), "VGK": ("Western", "Pacific"),
}


def upgrade() -> None:
    op.add_column('teams', sa.Column('conference', sa.String(length=30), nullable=True))
    op.add_column('teams', sa.Column('division', sa.String(length=30), nullable=True))

    conn = op.get_bind()
    for abbr, (conf, div) in ALIGNMENT.items():
        conn.execute(
            sa.text("UPDATE teams SET conference=:c, division=:d WHERE abbreviation=:a"),
            {"c": conf, "d": div, "a": abbr},
        )


def downgrade() -> None:
    op.drop_column('teams', 'division')
    op.drop_column('teams', 'conference')