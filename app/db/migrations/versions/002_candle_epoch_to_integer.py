"""002_candle_epoch_to_integer

Revision ID: 002_candle_epoch_to_integer
Revises: 001_initial
Create Date: 2026-05-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '002_candle_epoch_to_integer'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'candle',
        'epoch',
        type_=sa.Integer(),
        postgresql_using='EXTRACT(EPOCH FROM epoch)::INTEGER',
    )


def downgrade() -> None:
    op.alter_column(
        'candle',
        'epoch',
        type_=sa.DateTime(timezone=True),
        postgresql_using="to_timestamp(epoch)",
    )
