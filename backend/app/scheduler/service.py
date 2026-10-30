"""The only scheduler file that touches the database."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models.plan import SchedulerPlan
from .market import load_market
from .models import PlanResult, WorkloadSpec
from .optimizer import optimize


def plan_workload(
    session: Session,
    spec: WorkloadSpec,
    now: datetime | None = None,
    save: bool = True,
    user_id: int | None = None,
) -> PlanResult:
    """Call inside `with SessionLocal.begin() as s:` so the saved plan is committed."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    result = optimize(spec, load_market(session, now, spec.allowed_regions), now)
    if save:
        if user_id is None:
            raise ValueError("A user_id is required when saving a plan.")
        result.inputs["spec"] = {
            "name": spec.name,
            "duration_h": spec.duration_h,
            "deadline": spec.deadline,
            "mode": spec.mode,
            "min_vcpu": spec.min_vcpu,
            "min_memory_gb": spec.min_memory_gb,
            "min_gpus": spec.min_gpus,
            "allowed_regions": spec.allowed_regions,
            "checkpointing": spec.checkpointing,
        }
        b = result.best
        session.add(SchedulerPlan(
            user_id=user_id,
            workload_name=spec.name, mode=spec.mode, created_at=now, region=b.region, instance_type=b.instance,
            purchase_type=b.purchase, start_time=b.start, est_cost=b.cost, est_carbon_kg=b.carbon_kg,
            result=result.to_dict()))
    return result
