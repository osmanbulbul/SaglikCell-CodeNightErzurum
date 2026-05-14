"""Faz 4: goals, goal_progress, streaks tablolari eklendi

Revision ID: 96780f1b6214
Revises: 0e1b848f0ccf
Create Date: 2026-05-15 00:41:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '96780f1b6214'
down_revision: Union[str, None] = '0e1b848f0ccf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- goals tablosu ---
    op.create_table(
        'goals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('goal_type', sa.String(), nullable=False),
        sa.Column('target_value', sa.Float(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_goals_user_id', 'goals', ['user_id'])

    # --- goal_progress tablosu ---
    op.create_table(
        'goal_progress',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('goal_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('goals.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('current_value', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('progress_percentage', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('is_completed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_goal_progress_user_date', 'goal_progress', ['user_id', 'date'])

    # --- streaks tablosu ---
    op.create_table(
        'streaks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('streak_type', sa.String(), nullable=False),
        sa.Column('current_streak', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('longest_streak', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('last_activity_date', sa.Date(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_streaks_user_type', 'streaks', ['user_id', 'streak_type'])

    # --- DailySummary tablosuna yeni metrik kolonları (Faz 3 tamamlama) ---
    op.add_column('daily_summary', sa.Column('total_calories', sa.Float(), server_default=sa.text('0'), nullable=False))
    op.add_column('daily_summary', sa.Column('weight', sa.Float(), nullable=True))
    op.add_column('daily_summary', sa.Column('avg_heart_rate', sa.Float(), nullable=True))


def downgrade() -> None:
    # daily_summary ek kolonları geri al
    op.drop_column('daily_summary', 'avg_heart_rate')
    op.drop_column('daily_summary', 'weight')
    op.drop_column('daily_summary', 'total_calories')

    # streaks
    op.drop_index('ix_streaks_user_type', table_name='streaks')
    op.drop_table('streaks')

    # goal_progress
    op.drop_index('ix_goal_progress_user_date', table_name='goal_progress')
    op.drop_table('goal_progress')

    # goals
    op.drop_index('ix_goals_user_id', table_name='goals')
    op.drop_table('goals')
