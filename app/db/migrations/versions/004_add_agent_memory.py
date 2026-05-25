"""004_add_agent_memory

Revision ID: 004_add_agent_memory
Revises: 003_add_prompt_version
Create Date: 2026-05-25

Creates tables for agent short-term (agent_cycle) and long-term
(agent_lesson, agent_reflection) memory.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '004_add_agent_memory'
down_revision: Union[str, None] = '003_add_prompt_version'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'agent_cycle',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cycle_number', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbol', sa.String(), nullable=True),
        sa.Column('regime', sa.String(), nullable=True),
        sa.Column('m15_bias', sa.String(), nullable=True),
        sa.Column('time_window', sa.String(), nullable=True),
        sa.Column('confluence_call', sa.Integer(), nullable=True),
        sa.Column('confluence_put', sa.Integer(), nullable=True),
        sa.Column('llm_direction', sa.String(), nullable=True),
        sa.Column('llm_confidence', sa.Float(), nullable=True),
        sa.Column('llm_rationale', sa.Text(), nullable=True),
        sa.Column('llm_raw_response', sa.Text(), nullable=True),
        sa.Column('emitted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('signal_id', sa.Integer(), sa.ForeignKey('signal.id'), nullable=True),
        sa.Column('skip_reason', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'agent_reflection',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cycles_analyzed', sa.Integer(), nullable=True),
        sa.Column('model_used', sa.String(), nullable=True),
        sa.Column('trigger', sa.String(), nullable=True),
        sa.Column('raw_response', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'agent_lesson',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('topic', sa.String(), nullable=False, index=True),
        sa.Column('sample_size', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', index=True),
        sa.Column('last_reinforced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reflection_id', sa.Integer(), sa.ForeignKey('agent_reflection.id'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('agent_lesson')
    op.drop_table('agent_reflection')
    op.drop_table('agent_cycle')
