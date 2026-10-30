import secrets

from sqlalchemy import select

from ..models.core import OrgSettings, Workload
from ..models.execution import ExecutionRun, RunAttempt
from .schemas_v2 import WorkloadDetail, WorkloadSummary


def org_settings(db, org_id: int) -> OrgSettings:
    value = db.get(OrgSettings, org_id)
    if value is None:
        value = OrgSettings(org_id=org_id, aws_external_id=f"gc-ext-{secrets.token_hex(6)}")
        db.add(value)
        db.flush()
    return value


def _base(db, workload: Workload):
    run = db.get(ExecutionRun, workload.run_id) if workload.run_id else None
    attempts = (
        list(db.scalars(select(RunAttempt).where(RunAttempt.run_id == run.id).order_by(RunAttempt.number)))
        if run else []
    )
    best = (workload.plan or {}).get("best") or {}
    last = attempts[-1] if attempts else None
    return {
        "id": workload.id,
        "name": workload.name,
        "mode": workload.mode,
        "status": run.status if run else workload.status,
        "region": last.region if last else best.get("region"),
        "instance_type": last.instance_type if last else best.get("instance"),
        "est_cost": best.get("cost"),
        "actual_cost": run.actual_cost if run else None,
        "est_carbon_kg": best.get("carbon_kg"),
        "actual_carbon_kg": run.actual_carbon_kg if run else None,
        "deadline": workload.deadline,
        "created_at": workload.created_at,
    }, run, attempts


def summary(db, workload: Workload) -> WorkloadSummary:
    return WorkloadSummary.model_validate(_base(db, workload)[0])


def detail(db, workload: Workload) -> WorkloadDetail:
    base, run, attempts = _base(db, workload)
    run_dict = None
    if run:
        run_dict = {column.name: getattr(run, column.name) for column in ExecutionRun.__table__.columns}
        run_dict["attempts"] = [
            {column.name: getattr(attempt, column.name) for column in RunAttempt.__table__.columns}
            for attempt in attempts
        ]
    base.update(
        image=workload.image,
        workload_type=workload.workload_type,
        duration_h=workload.duration_h,
        min_vcpu=workload.min_vcpu,
        min_memory_gb=workload.min_memory_gb,
        min_gpus=workload.min_gpus,
        checkpointing=workload.checkpointing,
        allowed_regions=workload.allowed_regions,
        plan=workload.plan,
        run=run_dict,
    )
    return WorkloadDetail.model_validate(base)
