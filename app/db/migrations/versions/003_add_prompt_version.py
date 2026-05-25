"""003_add_prompt_version

Revision ID: 003_add_prompt_version
Revises: 002_candle_epoch_to_integer
Create Date: 2026-05-25

This migration creates the prompt_version table to store LLM system prompt versions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '003_add_prompt_version'
down_revision: Union[str, None] = '002_candle_epoch_to_integer'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'prompt_version',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false', index=True),
        sa.Column('note', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    from app.agent.prompts import SYSTEM_PROMPT_TEMPLATE
    from datetime import datetime, timezone

    op.execute(
        sa.insert(sa.table('prompt_version',
            sa.column('content'),
            sa.column('is_active'),
            sa.column('note'),
            sa.column('created_at')
        )).values(
            content=SYSTEM_PROMPT_TEMPLATE,
            is_active=True,
            note='seed inicial',
            created_at=datetime.now(timezone.utc)
        )
    )


def downgrade() -> None:
    op.drop_table('prompt_version')
