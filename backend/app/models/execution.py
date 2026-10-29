"""Run and attempt tables. Register: add `from .execution import ExecutionRun, RunAttempt` to
app/models/__init__.py, then `alembic revision --autogenerate -m "execution"` and `alembic upgrade head`."""
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class ExecutionRun(Base):
    __tablename__ = "execution_run"
    id: Mapped[int] = mapped_column(primary_key=True)
    workload_name: Mapped[str] = mapped_column(String(200))
    image: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(20), default="Scheduled", index=True)
    mode: Mapped[str] = mapped_column(String(20), default="Balanced")
    deadline: Mapped[datetime]
    duration_h: Mapped[float]
    min_vcpu: Mapped[int] = mapped_column(default=1)
    min_memory_gb: Mapped[float] = mapped_column(default=1)
    min_gpus: Mapped[int] = mapped_column(default=0)
    allowed_regions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    checkpointing: Mapped[bool] = mapped_column(default=True)
    progress: Mapped[float] = mapped_column(default=0.0)
    spot_relaunches: Mapped[int] = mapped_column(default=0)
    interruptions: Mapped[int] = mapped_column(default=0)
    launch_failures: Mapped[int] = mapped_column(default=0)
    deadline_at_risk: Mapped[bool] = mapped_column(default=False)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_heartbeat: Mapped[datetime | None] = mapped_column(nullable=True)
    est_cost: Mapped[float | None] = mapped_column(nullable=True)
    est_carbon_kg: Mapped[float | None] = mapped_column(nullable=True)
    actual_cost: Mapped[float] = mapped_column(default=0.0)
    actual_carbon_kg: Mapped[float] = mapped_column(default=0.0)
    wasted_h: Mapped[float] = mapped_column(default=0.0)       # hours of compute that produced no saved progress
    failure_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)


class RunAttempt(Base):
    __tablename__ = "run_attempt"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("execution_run.id"), index=True)
    number: Mapped[int]
    region: Mapped[str] = mapped_column(String(20))
    instance_type: Mapped[str] = mapped_column(String(30))
    purchase: Mapped[str] = mapped_column(String(12))
    instance_id: Mapped[str] = mapped_column(String(40))
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notice_at: Mapped[datetime | None] = mapped_column(nullable=True)
    start_progress: Mapped[float] = mapped_column(default=0.0)
    end_progress: Mapped[float | None] = mapped_column(nullable=True)
    price_per_h: Mapped[float] = mapped_column(default=0.0)
    kg_per_h: Mapped[float] = mapped_column(default=0.0)
    cost: Mapped[float] = mapped_column(default=0.0)
    carbon_kg: Mapped[float] = mapped_column(default=0.0)
    wasted_h: Mapped[float] = mapped_column(default=0.0)
