"""organization-scoped API tables

Revision ID: c8f1a2d3e4b5
Revises: b7c8d9e0f1a2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8f1a2d3e4b5"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The organization workload owns execution runs; legacy user_account ownership
    # is not available for app_user records.
    op.alter_column("execution_run", "user_id", nullable=True)
    op.create_table(
        "organization",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "app_user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=300), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_app_user_email", "app_user", ["email"], unique=False)
    op.create_index("ix_app_user_org_id", "app_user", ["org_id"], unique=False)
    op.create_table(
        "org_settings",
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organization.id"), primary_key=True),
        sa.Column("budget", sa.Float(), nullable=False),
        sa.Column("default_mode", sa.String(length=20), nullable=False),
        sa.Column("regions", sa.JSON(), nullable=False),
        sa.Column("aws_role_arn", sa.String(length=300), nullable=True),
        sa.Column("aws_external_id", sa.String(length=60), nullable=False),
        sa.Column("aws_connected", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "workload",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("image", sa.String(length=300), nullable=False),
        sa.Column("workload_type", sa.String(length=30), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("duration_h", sa.Float(), nullable=False),
        sa.Column("deadline", sa.DateTime(), nullable=False),
        sa.Column("min_vcpu", sa.Integer(), nullable=False),
        sa.Column("min_memory_gb", sa.Float(), nullable=False),
        sa.Column("min_gpus", sa.Integer(), nullable=False),
        sa.Column("allowed_regions", sa.JSON(), nullable=True),
        sa.Column("checkpointing", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("execution_run.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_workload_org_id", "workload", ["org_id"], unique=False)
    op.create_index("ix_workload_user_id", "workload", ["user_id"], unique=False)
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("target", sa.String(length=100), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_log_org_id", "audit_log", ["org_id"], unique=False)


def downgrade() -> None:
    op.alter_column("execution_run", "user_id", nullable=False)
    op.drop_index("ix_audit_log_org_id", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_workload_user_id", table_name="workload")
    op.drop_index("ix_workload_org_id", table_name="workload")
    op.drop_table("workload")
    op.drop_table("org_settings")
    op.drop_index("ix_app_user_org_id", table_name="app_user")
    op.drop_index("ix_app_user_email", table_name="app_user")
    op.drop_table("app_user")
    op.drop_table("organization")
