import calendar
import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...execution import states as S
from ...execution.manager import utcnow
from ...models.core import User, Workload
from ...models.execution import ExecutionRun
from ...models.market import CarbonIntensityRecord, PricingSnapshot, SpotPriceHistory
from ...scheduler.market import load_market
from ..deps import get_db
from ..helpers import summary
from ..schemas_v2 import CarbonNow, DashboardOut, Freshness, ReportOut
from ..security import current_user

router = APIRouter(tags=["insights"])
DONE = (S.COMPLETED, S.RECOVERED)


def _pairs(db: Session, user: User):
    query = select(Workload, ExecutionRun).join(
        ExecutionRun, Workload.run_id == ExecutionRun.id
    ).where(Workload.org_id == user.org_id)
    if user.role != "Admin":
        query = query.where(Workload.user_id == user.id)
    return db.execute(query).all()


def _baseline(workload: Workload) -> float:
    return float((workload.plan or {}).get("on_demand_cost") or 0)


def _pct(part: float, whole: float):
    return round(100 * part / whole, 1) if whole else None


def _months(pairs, count: int):
    now = utcnow()
    keys, year, month = [], now.year, now.month
    for _ in range(count):
        keys.append((year, month))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    keys.reverse()
    aggregate = {key: [0.0, 0.0, 0.0] for key in keys}
    for workload, run in pairs:
        if run.status in DONE and run.finished_at:
            values = aggregate.get((run.finished_at.year, run.finished_at.month))
            if values is not None:
                values[0] += _baseline(workload)
                values[1] += run.est_cost or 0
                values[2] += run.actual_cost
    return [
        {"month": f"{year}-{month:02d}", "label": calendar.month_abbr[month],
         "on_demand": round(values[0], 2), "estimated": round(values[1], 2), "actual": round(values[2], 2)}
        for (year, month), values in aggregate.items()
    ]


def _report(db: Session, user: User, months: int) -> dict:
    rows = _months(_pairs(db, user), months)
    for row in rows:
        row["variance_pct"] = _pct(row["actual"] - row["estimated"], row["estimated"])
    on_demand = sum(row["on_demand"] for row in rows)
    estimated = sum(row["estimated"] for row in rows)
    actual = sum(row["actual"] for row in rows)
    return {
        "rows": rows, "total_on_demand": round(on_demand, 2),
        "total_estimated": round(estimated, 2), "total_actual": round(actual, 2),
        "saved": round(on_demand - actual, 2), "saved_pct": _pct(on_demand - actual, on_demand),
    }


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    now, pairs = utcnow(), _pairs(db, user)
    done = [(w, r) for w, r in pairs if r.status in DONE and r.finished_at]
    month = [(w, r) for w, r in done if (r.finished_at.year, r.finished_at.month) == (now.year, now.month)]
    on_demand = sum(_baseline(w) for w, _ in month)
    actual = sum(r.actual_cost for _, r in month)
    run_now = sum((w.plan or {}).get("run_now_carbon_kg") or 0 for w, _ in month)
    carbon = sum(r.actual_carbon_kg for _, r in month)
    met = sum(r.finished_at <= w.deadline for w, r in done)
    query = select(Workload).where(Workload.org_id == user.org_id).order_by(Workload.id.desc())
    if user.role != "Admin":
        query = query.where(Workload.user_id == user.id)
    workloads = list(db.scalars(query))
    awaiting = sum(not w.run_id and w.status == "Awaiting approval" for w in workloads)
    running = sum(r.status in (S.SCHEDULED, S.RUNNING, S.RECOVERING) for _, r in pairs)
    current = sorted(load_market(db, now).carbon.items(), key=lambda item: item[1].g_per_kwh)
    return {
        "cost_saved": round(on_demand - actual, 2), "cost_saved_pct": _pct(on_demand - actual, on_demand),
        "carbon_avoided_kg": round(run_now - carbon, 3), "carbon_avoided_pct": _pct(run_now - carbon, run_now),
        "deadlines_met": met, "deadlines_total": len(done), "deadlines_met_pct": _pct(met, len(done)),
        "active_workloads": awaiting + running, "awaiting_approval": awaiting,
        "months": _months(pairs, 6),
        "carbon_now": [{"region": r, "g_per_kwh": c.g_per_kwh, "source": c.source, "observed_at": c.observed_at} for r, c in current],
        "recent": [summary(db, w) for w in workloads[:5]],
    }


@router.get("/reports", response_model=ReportOut)
def report(months: int = Query(6, ge=1, le=24), db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _report(db, user, months)


@router.get("/reports/export.csv")
def report_csv(months: int = Query(6, ge=1, le=24), db: Session = Depends(get_db), user: User = Depends(current_user)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["month", "on_demand_usd", "estimated_usd", "actual_usd", "variance_pct"])
    for row in _report(db, user, months)["rows"]:
        writer.writerow([row["month"], row["on_demand"], row["estimated"], row["actual"], row["variance_pct"]])
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=greencloud-report.csv"})


@router.get("/market/carbon", response_model=list[CarbonNow])
def market_carbon(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [
        {"region": region, "g_per_kwh": reading.g_per_kwh, "source": reading.source, "observed_at": reading.observed_at}
        for region, reading in sorted(load_market(db, utcnow()).carbon.items(), key=lambda item: item[1].g_per_kwh)
    ]


@router.get("/market/freshness", response_model=Freshness)
def freshness(db: Session = Depends(get_db), user: User = Depends(current_user)):
    now = utcnow()
    values = [
        db.scalar(select(func.max(SpotPriceHistory.observed_at))),
        db.scalar(select(func.max(PricingSnapshot.fetched_at))),
        db.scalar(select(func.max(CarbonIntensityRecord.observed_at))),
    ]
    ages = [None if value is None else round((now - value).total_seconds() / 60, 1) for value in values]
    return {"spot_latest": values[0], "pricing_latest": values[1], "carbon_latest": values[2],
            "spot_age_min": ages[0], "pricing_age_min": ages[1], "carbon_age_min": ages[2]}
