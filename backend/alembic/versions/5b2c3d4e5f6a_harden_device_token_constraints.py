"""harden device token uniqueness

Revision ID: 5b2c3d4e5f6a
Revises: 4e1a2b3c4d5e
"""

from alembic import op


revision = "5b2c3d4e5f6a"
down_revision = "4e1a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # batch mode keeps the migration portable to local SQLite development.
    with op.batch_alter_table("device_tokens") as batch_op:
        batch_op.create_unique_constraint("uq_device_tokens_user_device", ["user_id", "device_id"])
        batch_op.create_unique_constraint("uq_device_tokens_fcm_token", ["fcm_token"])


def downgrade() -> None:
    with op.batch_alter_table("device_tokens") as batch_op:
        batch_op.drop_constraint("uq_device_tokens_fcm_token", type_="unique")
        batch_op.drop_constraint("uq_device_tokens_user_device", type_="unique")
