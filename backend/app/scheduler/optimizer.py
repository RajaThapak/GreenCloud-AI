"""Pure function: workload + market snapshot in, ranked and explained plan out.
No database or network calls here, so it is easy to test and to explain."""
from __future__ import annotations

from datetime import datetime, timedelta

from . import config as C
from .candidates import build_candidates, eligible_instances
from .catalog import CATALOG
from .estimator import run_carbon_kg
from .explain import explain
from .forecast import BaselineForecaster
from .models import MarketSnapshot, NoEligibleInstance, NoFeasiblePlan, PlanResult, SchedulerError, WorkloadSpec
from .scoring import pick, rank, score_all

# Relaxation order: try the safe plan first, then give up the retry buffer and use on-demand.
LEVELS = [
    {"level": 0, "buffer": C.DEADLINE_BUFFER, "on_demand_only": False, "warn": None},
    {"level": 1, "buffer": 1.0, "on_demand_only": True,
     "warn": "Your deadline leaves no time for a retry, so this plan uses on-demand instances, which are not interrupted."},
]


def _stale_warnings(market: MarketSnapshot, now: datetime, regions: set) -> list[str]:
    w = []
    stale = sorted(r for r in regions if r in market.carbon
                   and now - market.carbon[r].observed_at > timedelta(hours=C.STALE_CARBON_H))
    if stale:
        w.append(f"Carbon data for {', '.join(stale)} is more than {C.STALE_CARBON_H} hours old.")
    if market.spot:
        newest = max(q.observed_at for q in market.spot.values())
        if now - newest > timedelta(hours=C.STALE_SPOT_H):
            w.append(f"No new Spot prices for {(now - newest).total_seconds() / 3600:.0f} hours. Check that the collectors are running.")
    return w


def optimize(spec: WorkloadSpec, market: MarketSnapshot, now: datetime, forecaster=None, catalog=None) -> PlanResult:
    catalog = catalog or CATALOG
    if spec.mode not in C.MODE_WEIGHTS:
        raise SchedulerError(f"Unknown optimization mode '{spec.mode}'. Use Cost, Balanced or Carbon.")
    if spec.duration_h <= 0:
        raise SchedulerError("Duration must be greater than 0 hours.")
    if spec.deadline <= now:
        raise SchedulerError("The deadline is already in the past.")
    if not market.spot and not market.on_demand:
        raise SchedulerError("No price data is available yet. Start the collectors first.")

    eligible = eligible_instances(spec, catalog)
    if not eligible:
        raise NoEligibleInstance(
            f"No tracked instance offers {spec.min_vcpu} vCPU, {spec.min_memory_gb:g} GB memory and {spec.min_gpus} GPU(s). Lower the requirements.")

    fc = forecaster or BaselineForecaster(market)
    for lvl in LEVELS:
        built = build_candidates(spec, market, fc, now, eligible, lvl["buffer"], lvl["on_demand_only"])
        if built.candidates:
            break
    else:
        raise NoFeasiblePlan(
            "No plan can finish before your deadline. Move the deadline later or shorten the duration.",
            earliest_finish=now + timedelta(hours=spec.duration_h))

    cands = built.candidates
    score_all(cands, spec.mode)
    best, alts = pick(rank(cands))

    od_quote = market.on_demand.get((best.region, best.instance))
    on_demand_cost = od_quote.price * spec.duration_h if od_quote else None
    run_now = None
    if C.DEFAULT_REGION in market.carbon:
        run_now = run_carbon_kg(fc, C.DEFAULT_REGION, catalog[best.instance], now, spec.duration_h)

    warnings = [lvl["warn"]] if lvl["warn"] else []
    for region, inst in sorted(built.fallbacks):
        if region in {best.region, *[a.region for a in alts]}:
            warnings.append(f"No Spot price for {inst} in {region}, so on-demand pricing was used there.")
    if built.skipped_no_carbon:
        warnings.append(f"Skipped {', '.join(sorted(built.skipped_no_carbon))}: no carbon data.")
    warnings += _stale_warnings(market, now, {c.region for c in cands})

    spot_q = market.spot.get((best.region, best.instance))
    carbon_r = market.carbon.get(best.region)
    inputs = {
        "now": now, "mode": spec.mode, "weights": C.MODE_WEIGHTS[spec.mode], "buffer": lvl["buffer"],
        "relaxation_level": lvl["level"], "forecaster": getattr(fc, "name", type(fc).__name__),
        "candidates_considered": len(cands),
        "assumptions": {"PUE": C.PUE, "watts_per_vcpu": C.WATTS_PER_VCPU, "watts_per_gpu": C.WATTS_PER_GPU},
        "best_spot_quote": {"price": spot_q.price, "observed_at": spot_q.observed_at} if spot_q else None,
        "best_carbon": {"g_per_kwh": carbon_r.g_per_kwh, "observed_at": carbon_r.observed_at, "source": carbon_r.source},
    }
    return PlanResult(best=best, alternatives=alts, reasons=explain(spec, best, alts, cands, on_demand_cost, run_now),
                      warnings=warnings, on_demand_cost=on_demand_cost, run_now_carbon_kg=run_now,
                      relaxation_level=lvl["level"], inputs=inputs)
