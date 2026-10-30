from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models.execution import ExecutionRun
from ..models.market import CarbonIntensityRecord, PricingSnapshot, SpotPriceHistory
from ..models.plan import SchedulerPlan
from ..models.user import User
from ..scheduler.models import NoEligibleInstance, NoFeasiblePlan, SchedulerError, WorkloadSpec
from ..scheduler.catalog import CATALOG
from ..scheduler.service import plan_workload
from .schemas import (
    AuthRequest,
    AuthResponse,
    DashboardSummary,
    PlanRequest,
    PlanResponse,
    PlanSummary,
    SettingsResponse,
    SettingsUpdate,
    SignupRequest,
    UserResponse,
    WorkloadResponse,
)
from .auth import create_access_token, get_current_user, hash_password, verify_password

api = APIRouter(prefix="/api")
auth = APIRouter(prefix="/auth", tags=["auth"])
dashboard = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)])
workloads = APIRouter(prefix="/workloads", tags=["workloads"], dependencies=[Depends(get_current_user)])
reports = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(get_current_user)])
settings = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_user)])
market = APIRouter(prefix="/market", tags=["market"], dependencies=[Depends(get_current_user)])
plans = APIRouter(prefix="/plans", tags=["plans"], dependencies=[Depends(get_current_user)])


def get_db():
    with SessionLocal() as session:
        yield session


def _workload_response(run: ExecutionRun) -> WorkloadResponse:
    return WorkloadResponse(
        id=run.id,
        name=run.workload_name,
        image=run.image,
        status=run.status,
        mode=run.mode,
        deadline=run.deadline,
        duration=run.duration_h,
        vcpu=run.min_vcpu,
        memory=run.min_memory_gb,
        gpu=run.min_gpus,
        progress=run.progress,
        est_cost=run.est_cost,
        est_carbon=run.est_carbon_kg,
        actual_cost=run.actual_cost,
        actual_carbon=run.actual_carbon_kg,
        started_at=run.started_at,
        finished_at=run.finished_at,
        failure_reason=run.failure_reason,
    )


@auth.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from None
    db.refresh(user)
    return AuthResponse(access_token=create_access_token(user), user=user)


@auth.post("/login", response_model=AuthResponse)
def login(payload: AuthRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return AuthResponse(access_token=create_access_token(user), user=user)


@auth.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.tokens_valid_after = datetime.utcnow()
    db.commit()
    return None


@auth.get("/me", response_model=UserResponse)
def current_user(user: User = Depends(get_current_user)):
    return user


@dashboard.get("/summary", response_model=DashboardSummary)
def dashboard_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    runs = list(db.scalars(select(ExecutionRun).where(ExecutionRun.user_id == user.id)))
    estimated = sum(run.est_cost or 0 for run in runs)
    actual = sum(run.actual_cost or 0 for run in runs)
    active = sum(run.status in {"Scheduled", "Running", "Awaiting"} for run in runs)
    awaiting = sum(run.status == "Awaiting" for run in runs)
    completed = [run for run in runs if run.status == "Completed"]
    compliance = sum(not run.deadline_at_risk for run in completed) / len(completed) * 100 if completed else 0
    return DashboardSummary(
        cost_saved=round(max(estimated - actual, 0), 2),
        carbon_avoided=round(sum(run.est_carbon_kg or 0 for run in runs), 2),
        deadline_compliance=round(compliance, 1),
        active_workloads=active,
        awaiting_approval=awaiting,
    )


@dashboard.get("/cost-over-time")
def dashboard_cost_over_time(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    grouped = {}
    for plan in db.scalars(select(SchedulerPlan).where(SchedulerPlan.user_id == user.id).order_by(SchedulerPlan.created_at)):
        month = plan.created_at.strftime("%b")
        entry = grouped.setdefault(month, {"month": month, "onDemand": 0.0, "withGC": 0.0})
        entry["withGC"] += float(plan.est_cost or 0)
        entry["onDemand"] += float(plan.result.get("on_demand_cost") or plan.est_cost or 0)
    return list(grouped.values())


@dashboard.get("/carbon-intensity")
def dashboard_carbon_intensity(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            CarbonIntensityRecord.region,
            CarbonIntensityRecord.intensity,
            CarbonIntensityRecord.observed_at,
        ).order_by(CarbonIntensityRecord.region, CarbonIntensityRecord.observed_at.desc())
    ).all()
    latest = {}
    for region, intensity, observed_at in rows:
        latest.setdefault(region, {"region": region, "value": float(intensity), "observedAt": observed_at})
    maximum = max((item["value"] for item in latest.values()), default=1)
    return [{**item, "pct": round(item["value"] / maximum * 100)} for item in latest.values()]


@dashboard.get("/mode-breakdown")
def dashboard_mode_breakdown(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(SchedulerPlan.mode, func.count(SchedulerPlan.id))
        .where(SchedulerPlan.user_id == user.id)
        .group_by(SchedulerPlan.mode)
        .order_by(SchedulerPlan.mode)
    ).all()
    total = sum(count for _, count in rows)
    return [
        {"mode": mode, "count": count, "percent": round(count / total * 100, 1) if total else 0}
        for mode, count in rows
    ]


@dashboard.get("/recent-workloads", response_model=list[WorkloadResponse])
def dashboard_recent_workloads(
    limit: int = Query(default=6, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    runs = db.scalars(
        select(ExecutionRun).where(ExecutionRun.user_id == user.id).order_by(ExecutionRun.id.desc()).limit(limit)
    )
    return [_workload_response(run) for run in runs]


@workloads.get("", response_model=list[WorkloadResponse])
def list_workloads(
    status_filter: str | None = Query(default=None, alias="status"),
    mode: str | None = None,
    search: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(ExecutionRun).where(ExecutionRun.user_id == user.id).order_by(ExecutionRun.id.desc())
    if status_filter:
        query = query.where(ExecutionRun.status == status_filter)
    if mode:
        query = query.where(ExecutionRun.mode == mode)
    if search:
        query = query.where(ExecutionRun.workload_name.ilike(f"%{search}%"))
    return [_workload_response(run) for run in db.scalars(query)]


@workloads.get("/{workload_id}", response_model=WorkloadResponse)
def get_workload(workload_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = db.scalar(select(ExecutionRun).where(ExecutionRun.id == workload_id, ExecutionRun.user_id == user.id))
    if run is None:
        raise HTTPException(status_code=404, detail="Workload not found.")
    return _workload_response(run)


@workloads.post("/plan", response_model=PlanResponse)
def generate_plan(payload: PlanRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        result = plan_workload(db, payload.to_spec(), save=True, user_id=user.id)
        db.flush()
        saved_plan = db.scalars(
            select(SchedulerPlan).where(SchedulerPlan.user_id == user.id).order_by(SchedulerPlan.id.desc())
        ).first()
        db.commit()
    except (SchedulerError, NoEligibleInstance, NoFeasiblePlan) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response = result.to_dict()
    response["plan_id"] = saved_plan.id
    return PlanResponse.model_validate(response)


@plans.get("", response_model=list[PlanSummary])
def list_plans(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(SchedulerPlan).where(SchedulerPlan.user_id == user.id).order_by(SchedulerPlan.id.desc())))


@plans.get("/{plan_id}", response_model=PlanSummary)
def get_plan(plan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.scalar(select(SchedulerPlan).where(SchedulerPlan.id == plan_id, SchedulerPlan.user_id == user.id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return plan


@plans.post("/{plan_id}/schedule", response_model=WorkloadResponse, status_code=status.HTTP_201_CREATED)
def schedule_plan(plan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.scalar(select(SchedulerPlan).where(SchedulerPlan.id == plan_id, SchedulerPlan.user_id == user.id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    inputs = plan.result.get("inputs", {})
    spec_inputs = inputs.get("spec", {})
    run = ExecutionRun(
        user_id=user.id,
        workload_name=plan.workload_name,
        mode=plan.mode,
        status="Scheduled",
        deadline=plan.start_time + timedelta(hours=spec_inputs.get("duration_h", 1)),
        duration_h=spec_inputs.get("duration_h", 1),
        min_vcpu=spec_inputs.get("min_vcpu", 1),
        min_memory_gb=spec_inputs.get("min_memory_gb", 1),
        min_gpus=spec_inputs.get("min_gpus", 0),
        allowed_regions=spec_inputs.get("allowed_regions"),
        est_cost=plan.est_cost,
        est_carbon_kg=plan.est_carbon_kg,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return _workload_response(run)


@workloads.post("/{workload_id}/cancel", response_model=WorkloadResponse)
def cancel_workload(workload_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = db.scalar(select(ExecutionRun).where(ExecutionRun.id == workload_id, ExecutionRun.user_id == user.id))
    if run is None:
        raise HTTPException(status_code=404, detail="Workload not found.")
    if run.status in {"Completed", "Failed", "Cancelled"}:
        raise HTTPException(status_code=409, detail=f"Workload is already {run.status.lower()}.")
    run.status = "Cancelled"
    db.commit()
    db.refresh(run)
    return _workload_response(run)


@reports.get("/summary")
def report_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plans = list(db.scalars(select(SchedulerPlan).where(SchedulerPlan.user_id == user.id)))
    return {
        "totalSaved": round(sum(max((plan.est_cost or 0) * 0.34, 0) for plan in plans), 2),
        "carbonAvoided": round(sum(plan.est_carbon_kg or 0 for plan in plans), 2),
        "jobsScheduled": len(plans),
    }


@reports.get("/cost-savings")
def report_cost_savings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return dashboard_cost_over_time(user, db)


@reports.get("/carbon-trend")
def report_carbon_trend(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(CarbonIntensityRecord.region, CarbonIntensityRecord.intensity, CarbonIntensityRecord.observed_at)
        .order_by(CarbonIntensityRecord.observed_at)
    ).all()
    grouped = defaultdict(dict)
    for region, intensity, observed_at in rows:
        grouped[observed_at.isoformat()]["time"] = observed_at.isoformat()
        grouped[observed_at.isoformat()][region] = float(intensity)
    return list(grouped.values())


@reports.get("/spot-prices")
def report_spot_prices(
    instance_type: str | None = None,
    region: str | None = None,
    db: Session = Depends(get_db),
):
    query = select(SpotPriceHistory).order_by(SpotPriceHistory.observed_at)
    if instance_type:
        query = query.where(SpotPriceHistory.instance_type == instance_type)
    if region:
        query = query.where(SpotPriceHistory.region == region)
    grouped = defaultdict(dict)
    for row in db.scalars(query):
        grouped[row.observed_at.isoformat()]["time"] = row.observed_at.isoformat()
        grouped[row.observed_at.isoformat()][row.region] = float(row.spot_price)
    return list(grouped.values())


@reports.get("/mode-breakdown")
def report_mode_breakdown(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(SchedulerPlan.mode, func.count(SchedulerPlan.id))
        .where(SchedulerPlan.user_id == user.id)
        .group_by(SchedulerPlan.mode)
        .order_by(SchedulerPlan.mode)
    ).all()
    total = sum(count for _, count in rows)
    return [
        {"mode": mode, "count": count, "percent": round(count / total * 100, 1) if total else 0}
        for mode, count in rows
    ]


@settings.get("", response_model=SettingsResponse)
def get_settings():
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Settings persistence is not configured. Add a settings store before enabling this endpoint.",
    )


@settings.patch("", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdate):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Settings persistence is not configured. Add a settings store before enabling this endpoint.",
    )


@market.get("/regions")
def list_regions(db: Session = Depends(get_db)):
    regions = db.execute(
        select(CarbonIntensityRecord.region).union(
            select(PricingSnapshot.region),
            select(SpotPriceHistory.region),
        ).order_by("region")
    ).scalars().all()
    return {"regions": regions}


@market.get("/instances")
def list_instances():
    return [
        {"name": name, "vcpu": spec.vcpu, "memoryGb": spec.memory_gb, "gpus": spec.gpus}
        for name, spec in CATALOG.items()
    ]


api.include_router(auth)
api.include_router(dashboard)
api.include_router(workloads)
api.include_router(reports)
api.include_router(settings)
api.include_router(market)
api.include_router(plans)
