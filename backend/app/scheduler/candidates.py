from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .config import (DEFAULT_INTERRUPTION, LOST_WORK_CHECKPOINT, LOST_WORK_NO_CHECKPOINT,
                     MAX_HORIZON_H, START_STEP_H)
from .estimator import risk_label, run_carbon_kg, run_cost
from .models import Candidate, InstanceSpec, MarketSnapshot, WorkloadSpec


@dataclass
class Built:
    candidates: list = field(default_factory=list)
    fallbacks: set = field(default_factory=set)         # (region, instance) priced on-demand because no Spot data
    skipped_no_carbon: set = field(default_factory=set)


def eligible_instances(spec: WorkloadSpec, catalog: dict) -> list[InstanceSpec]:
    return [i for i in catalog.values()
            if i.vcpu >= spec.min_vcpu and i.memory_gb >= spec.min_memory_gb and i.gpus >= spec.min_gpus]


def start_times(spec: WorkloadSpec, now: datetime, buffer: float) -> list[datetime]:
    latest = spec.deadline - timedelta(hours=spec.duration_h * buffer)
    out, t = [], now
    while t <= latest and t - now <= timedelta(hours=MAX_HORIZON_H):
        out.append(t)
        t += timedelta(hours=START_STEP_H)
    return out


def build_candidates(spec, market: MarketSnapshot, fc, now, eligible, buffer: float, on_demand_only: bool) -> Built:
    built = Built()
    starts = start_times(spec, now, buffer)
    regions = spec.allowed_regions or sorted({r for r, _ in market.spot} | {r for r, _ in market.on_demand})
    lost = LOST_WORK_CHECKPOINT if spec.checkpointing else LOST_WORK_NO_CHECKPOINT
    for region in regions:
        if region not in market.carbon:
            built.skipped_no_carbon.add(region)
            continue
        for inst in eligible:
            key = (region, inst.name)
            if on_demand_only:
                purchase = "On-demand" if key in market.on_demand else None
            elif key in market.spot:
                purchase = "Spot"
            elif key in market.on_demand:
                purchase = "On-demand"
                built.fallbacks.add(key)
            else:
                purchase = None
            if purchase is None:
                continue
            chance = 0.0 if purchase == "On-demand" else market.interruption.get(inst.family, DEFAULT_INTERRUPTION)
            for start in starts:
                cost = run_cost(fc, region, inst, purchase, start, spec.duration_h)
                carbon = run_carbon_kg(fc, region, inst, start, spec.duration_h)
                if cost is None or carbon is None:
                    continue
                built.candidates.append(Candidate(
                    region=region, instance=inst.name, purchase=purchase, start=start,
                    finish=start + timedelta(hours=spec.duration_h), cost=cost,
                    risk_adj_cost=cost * (1 + chance * lost), carbon_kg=carbon,
                    risk_chance=chance, risk_label=risk_label(chance)))
    return built
