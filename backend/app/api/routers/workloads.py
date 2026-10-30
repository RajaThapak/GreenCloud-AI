from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...execution import states as S
from ...execution.manager import utcnow
from ...models.core import User, Workload
from ...models.execution import ExecutionRun
from ...scheduler.models import WorkloadSpec
from ...scheduler.presets import suggest
from ...scheduler.service import plan_workload
from ..audit import audit
from ..deps import get_cloud, get_db, make_manager
from ..errors import ApiError
from ..helpers import detail, org_settings, summary
from ..schemas_v2 import ReplanIn, RequirementsIn, WorkloadDetail, WorkloadIn, WorkloadSummary
from ..security import current_user

router = APIRouter(tags=["workloads"])


def _owned(db: Session, user: User, workload_id: int) -> Workload:
    workload = db.get(Workload, workload_id)
    if workload is None or workload.org_id != user.org_id or (
        user.role != "Admin" and workload.user_id != user.id
    ):
        raise ApiError(404, "We could not find that workload.", "not_found")
    return workload


def _spec(workload: Workload, mode: str | None = None) -> WorkloadSpec:
    return WorkloadSpec(
        workload.name, workload.duration_h, workload.deadline, mode or workload.mode,
        workload.min_vcpu, workload.min_memory_gb, workload.min_gpus,
        workload.allowed_regions or None, workload.checkpointing,
    )


def _month_spend(db: Session, org_id: int) -> float:
    first = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    query = (
        select(func.coalesce(func.sum(ExecutionRun.actual_cost), 0.0))
        .select_from(ExecutionRun)
        .join(Workload, Workload.run_id == ExecutionRun.id)
        .where(Workload.org_id == org_id, ExecutionRun.started_at >= first)
    )
    return float(db.scalar(query) or 0)


@router.post("/requirements/suggest")
def requirements(body: RequirementsIn, user: User = Depends(current_user)):
    result = suggest(body.workload_type, body.needs_gpu)
    return {"vcpu": result["vcpu"], "memory_gb": result["memory_gb"], "gpus": result["gpus"], "note": result["note"]}


@router.post("/workloads", response_model=WorkloadDetail, status_code=201)
def create_workload(body: WorkloadIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    org = org_settings(db, user.org_id)
    allowed = body.allowed_regions or org.regions or None
    spec = WorkloadSpec(
        body.name, body.duration_h, body.deadline, body.mode, body.min_vcpu,
        body.min_memory_gb, body.min_gpus, allowed, body.checkpointing,
    )
    result = plan_workload(db, spec, save=False)
    workload = Workload(
        org_id=user.org_id, user_id=user.id, name=body.name, image=body.image,
        workload_type=body.workload_type, mode=body.mode, duration_h=body.duration_h,
        deadline=body.deadline, min_vcpu=body.min_vcpu, min_memory_gb=body.min_memory_gb,
        min_gpus=body.min_gpus, allowed_regions=allowed, checkpointing=body.checkpointing,
        plan=result.to_dict(),
    )
    db.add(workload)
    db.flush()
    audit(db, user, "workload.create", workload.id, {"mode": workload.mode})
    db.commit()
    return detail(db, workload)


@router.get("/workloads", response_model=list[WorkloadSummary])
def list_workloads(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = select(Workload).where(Workload.org_id == user.org_id).order_by(Workload.id.desc())
    if user.role != "Admin":
        query = query.where(Workload.user_id == user.id)
    rows = [summary(db, row) for row in db.scalars(query)]
    return [row for row in rows if not status or row.status == status]


@router.get("/workloads/{workload_id}", response_model=WorkloadDetail)
def get_workload(workload_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return detail(db, _owned(db, user, workload_id))


@router.post("/workloads/{workload_id}/replan", response_model=WorkloadDetail)
def replan(workload_id: int, body: ReplanIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    workload = _owned(db, user, workload_id)
    if workload.run_id or workload.status != "Awaiting approval":
        raise ApiError(409, "Only plans that are waiting for approval can be changed.", "not_editable")
    workload.plan = plan_workload(db, _spec(workload, body.mode), save=False).to_dict()
    workload.mode = body.mode
    audit(db, user, "workload.replan", workload.id, {"mode": body.mode})
    db.commit()
    return detail(db, workload)


@router.post("/workloads/{workload_id}/approve", response_model=WorkloadDetail)
def approve(workload_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    workload = _owned(db, user, workload_id)
    if workload.run_id or workload.status != "Awaiting approval":
        raise ApiError(409, "This workload was already approved or cancelled.", "not_editable")
    best = workload.plan["best"]
    cap = org_settings(db, user.org_id).budget
    if _month_spend(db, user.org_id) + best["cost"] > cap:
        raise ApiError(409, f"Approving this plan would exceed your monthly budget cap of ${cap:.2f}.", "budget_cap")
    run = ExecutionRun(
        user_id=None, workload_name=workload.name, image=workload.image, mode=workload.mode,
        deadline=workload.deadline, duration_h=workload.duration_h, min_vcpu=workload.min_vcpu,
        min_memory_gb=workload.min_memory_gb, min_gpus=workload.min_gpus,
        allowed_regions=workload.allowed_regions, checkpointing=workload.checkpointing,
        est_cost=best["cost"], est_carbon_kg=best["carbon_kg"],
    )
    db.add(run)
    db.flush()
    workload.run_id, workload.status = run.id, "Scheduled"
    make_manager(db, get_cloud()).start(run.id)
    audit(db, user, "workload.approve", workload.id, {"region": best["region"], "purchase": best["purchase"]})
    db.commit()
    return detail(db, workload)


@router.post("/workloads/{workload_id}/cancel", response_model=WorkloadDetail)
def cancel(workload_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    workload = _owned(db, user, workload_id)
    run = db.get(ExecutionRun, workload.run_id) if workload.run_id else None
    if workload.status == "Cancelled" or (run and run.status in S.TERMINAL):
        raise ApiError(409, "This workload has already finished or been cancelled.", "not_editable")
    if run:
        make_manager(db, get_cloud()).cancel(run.id)
    else:
        workload.status = "Cancelled"
    audit(db, user, "workload.cancel", workload.id)
    db.commit()
    return detail(db, workload)
