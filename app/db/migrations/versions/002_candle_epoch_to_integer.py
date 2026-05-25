"""002_candle_epoch_to_integer

Revision ID: 002_candle_epoch_to_integer
Revises: 001_initial
Create Date: 2026-05-24

This migration converts the candle.epoch column from DateTime to Integer.
It's idempotent - if the column is already Integer, it gracefully skips the conversion.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = '002_candle_epoch_to_integer'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if column is already Integer to make migration idempotent
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_name = 'candle' AND column_name = 'epoch'
    """))
    col_type = result.scalar()

    if col_type and 'integer' not in col_type.lower():
        # Only alter if it's not already an integer type
        op.alter_column(
            'candle',
            'epoch',
            type_=sa.Integer(),
            postgresql_using=r'CAST(EXTRACT(EPOCH FROM epoch::timestamp) AS INTEGER)',
        )


def downgrade() -> None:
    op.alter_column(
        'candle',
        'epoch',
        type_=sa.DateTime(timezone=True),
        postgresql_using="to_timestamp(epoch)",
    )
