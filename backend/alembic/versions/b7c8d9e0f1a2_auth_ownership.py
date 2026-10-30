"""add authentication ownership and token revocation fields

Revision ID: b7c8d9e0f1a2
Revises: 8f1a2c3d4e5f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "8f1a2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_account", sa.Column("tokens_valid_after", sa.DateTime(), nullable=True))

    op.add_column("scheduler_plan", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index("ix_scheduler_plan_user_id", "scheduler_plan", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_scheduler_plan_user_id_user_account",
        "scheduler_plan",
        "user_account",
        ["user_id"],
        ["id"],
    )
    connection = op.get_bind()
    existing_plans = connection.execute(
        sa.text("SELECT COUNT(*) FROM scheduler_plan")
    ).scalar_one()
    if existing_plans:
        raise RuntimeError(
            "Cannot migrate scheduler plans to user ownership automatically. "
            "Assign each existing plan to its owner before applying this migration."
        )
    op.alter_column("scheduler_plan", "user_id", nullable=False)

    op.add_column("execution_run", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index("ix_execution_run_user_id", "execution_run", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_execution_run_user_id_user_account",
        "execution_run",
        "user_account",
        ["user_id"],
        ["id"],
    )
    existing_runs = connection.execute(
        sa.text("SELECT COUNT(*) FROM execution_run")
    ).scalar_one()
    if existing_runs:
        raise RuntimeError(
            "Cannot migrate execution runs to user ownership automatically. "
            "Assign each existing workload to its owner before applying this migration."
        )
    op.alter_column("execution_run", "user_id", nullable=False)


def downgrade() -> None:
    op.drop_constraint("fk_execution_run_user_id_user_account", "execution_run", type_="foreignkey")
    op.drop_index("ix_execution_run_user_id", table_name="execution_run")
    op.drop_column("execution_run", "user_id")
    op.drop_constraint("fk_scheduler_plan_user_id_user_account", "scheduler_plan", type_="foreignkey")
    op.drop_index("ix_scheduler_plan_user_id", table_name="scheduler_plan")
    op.drop_column("scheduler_plan", "user_id")
    op.drop_column("user_account", "tokens_valid_after")
