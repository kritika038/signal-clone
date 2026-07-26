"""add_device_tokens_table

Revision ID: 4e1a2b3c4d5e
Revises: 3d2dcb3f8b00
Create Date: 2026-07-26 17:41:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e1a2b3c4d5e'
down_revision: Union[str, None] = '3d2dcb3f8b00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'device_tokens',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('device_id', sa.String(length=255), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('fcm_token', sa.String(length=512), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_device_tokens_user_id'), 'device_tokens', ['user_id'], unique=False)
    op.create_index(op.f('ix_device_tokens_device_id'), 'device_tokens', ['device_id'], unique=False)
    op.create_index(op.f('ix_device_tokens_fcm_token'), 'device_tokens', ['fcm_token'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_device_tokens_fcm_token'), table_name='device_tokens')
    op.drop_index(op.f('ix_device_tokens_device_id'), table_name='device_tokens')
    op.drop_index(op.f('ix_device_tokens_user_id'), table_name='device_tokens')
    op.drop_table('device_tokens')
