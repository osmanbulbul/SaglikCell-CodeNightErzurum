"""Faz 5.7: Sorgu optimizasyonu - daily_summary ve metrics tablolarına ek indeksler

Revision ID: a3f9c2e18b05
Revises: 96780f1b6214
Create Date: 2026-05-15 00:48:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = 'a3f9c2e18b05'
down_revision: Union[str, None] = '96780f1b6214'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Analitik sorgular daily_summary tablosunu yoğun kullanır.
    user_id + date birleşik indeksi trend ve karşılaştırma sorgularını hızlandırır.
    metrics tablosunda metric_type filtrelemesi için ek indeks ekliyoruz.
    """
    # daily_summary: user_id + date birleşik indeks (trend sorguları için kritik)
    op.create_index(
        'ix_daily_summary_user_date',
        'daily_summary',
        ['user_id', 'date'],
    )

    # metrics: user_id + metric_type + timestamp (öğün dağılımı ve tip bazlı sorgular için)
    op.create_index(
        'ix_metrics_user_type_time',
        'metrics',
        ['user_id', 'metric_type', 'timestamp'],
    )

    # goal_progress: user_id + is_completed (rozet ve tamamlanma sayımı için)
    op.create_index(
        'ix_goal_progress_completed',
        'goal_progress',
        ['user_id', 'is_completed'],
    )


def downgrade() -> None:
    op.drop_index('ix_goal_progress_completed', table_name='goal_progress')
    op.drop_index('ix_metrics_user_type_time', table_name='metrics')
    op.drop_index('ix_daily_summary_user_date', table_name='daily_summary')
