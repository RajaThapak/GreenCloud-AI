"""user accounts

Revision ID: 8f1a2c3d4e5f
Revises: 42e030d63cba
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f1a2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "42e030d63cba"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_account",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_user_account_email"),
    )
    op.create_index(op.f("ix_user_account_email"), "user_account", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_account_email"), table_name="user_account")
    op.drop_table("user_account")
