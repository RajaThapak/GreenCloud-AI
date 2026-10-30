"""Saved plans. Register it: add `from .plan import SchedulerPlan` to app/models/__init__.py,
then run `alembic revision --autogenerate -m "scheduler plan"` and `alembic upgrade head`."""
from datetime import datetime

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class SchedulerPlan(Base):
    __tablename__ = "scheduler_plan"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"), index=True)
    workload_name: Mapped[str] = mapped_column(String(200))
    mode: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime]
    region: Mapped[str] = mapped_column(String(20))
    instance_type: Mapped[str] = mapped_column(String(30))
    purchase_type: Mapped[str] = mapped_column(String(12))
    start_time: Mapped[datetime]
    est_cost: Mapped[float]
    est_carbon_kg: Mapped[float]
    result: Mapped[dict] = mapped_column(JSON)    # full PlanResult, including the inputs it used
