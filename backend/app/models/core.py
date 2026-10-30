from datetime import datetime, timezone

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Organization(Base):
    __tablename__ = "organization"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(default=_now)


class User(Base):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(10), default="User")
    org_id: Mapped[int] = mapped_column(ForeignKey("organization.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class OrgSettings(Base):
    __tablename__ = "org_settings"

    org_id: Mapped[int] = mapped_column(ForeignKey("organization.id"), primary_key=True)
    budget: Mapped[float] = mapped_column(default=500.0)
    default_mode: Mapped[str] = mapped_column(String(20), default="Balanced")
    regions: Mapped[list] = mapped_column(JSON, default=list)
    aws_role_arn: Mapped[str | None] = mapped_column(String(300), nullable=True)
    aws_external_id: Mapped[str] = mapped_column(String(60), default="")
    aws_connected: Mapped[bool] = mapped_column(default=False)


class Workload(Base):
    __tablename__ = "workload"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organization.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    image: Mapped[str] = mapped_column(String(300))
    workload_type: Mapped[str] = mapped_column(String(30))
    mode: Mapped[str] = mapped_column(String(20))
    duration_h: Mapped[float]
    deadline: Mapped[datetime]
    min_vcpu: Mapped[int]
    min_memory_gb: Mapped[float]
    min_gpus: Mapped[int]
    allowed_regions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    checkpointing: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(String(20), default="Awaiting approval")
    plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("execution_run.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(index=True)
    user_id: Mapped[int | None] = mapped_column(nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    target: Mapped[str] = mapped_column(String(100), default="")
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)
