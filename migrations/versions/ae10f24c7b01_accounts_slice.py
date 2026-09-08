"""accounts slice: users, sessions, favorites, event prefs

Revision ID: ae10f24c7b01
Revises: 333a3d9a45d5
Create Date: 2026-09-08 15:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ae10f24c7b01'
down_revision: str | Sequence[str] | None = '333a3d9a45d5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=60), nullable=False),
        sa.Column('display_name', sa.String(length=120), nullable=True),
        sa.Column('passkey_hash', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_table('session_tokens',
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('token')
    )
    op.create_index(op.f('ix_session_tokens_user_id'), 'session_tokens', ['user_id'], unique=False)
    op.create_table('favorites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('item_type', sa.String(length=20), nullable=False),
        sa.Column('item_key', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'item_type', 'item_key')
    )
    op.create_index(op.f('ix_favorites_user_id'), 'favorites', ['user_id'], unique=False)
    op.create_table('user_event_prefs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('event_key', sa.String(length=40), nullable=False),
        sa.Column('lead_days', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'event_key')
    )
    op.create_index(op.f('ix_user_event_prefs_user_id'), 'user_event_prefs', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_user_event_prefs_user_id'), table_name='user_event_prefs')
    op.drop_table('user_event_prefs')
    op.drop_index(op.f('ix_favorites_user_id'), table_name='favorites')
    op.drop_table('favorites')
    op.drop_index(op.f('ix_session_tokens_user_id'), table_name='session_tokens')
    op.drop_table('session_tokens')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')