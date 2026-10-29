from __future__ import annotations

import math
from datetime import datetime, timedelta

from .config import LOW_RISK_MAX, MEDIUM_RISK_MAX, PUE
from .models import InstanceSpec


def run_slots(start: datetime, duration_h: float):
    """Hour-by-hour slots of a run. The last slot may be partial (weight < 1)."""
    n = math.ceil(duration_h - 1e-9)
    return [(start + timedelta(hours=i), min(1.0, duration_h - i)) for i in range(n)]


def run_cost(fc, region: str, inst: InstanceSpec, purchase: str, start: datetime, duration_h: float):
    total = 0.0
    for t, w in run_slots(start, duration_h):
        p = fc.spot_price(region, inst.name, t) if purchase == "Spot" else fc.on_demand_price(region, inst.name)
        if p is None:
            return None
        total += p * w
    return total


def run_carbon_kg(fc, region: str, inst: InstanceSpec, start: datetime, duration_h: float):
    total_g = 0.0
    for t, w in run_slots(start, duration_h):
        g = fc.carbon(region, t)
        if g is None:
            return None
        total_g += inst.power_kw * PUE * w * g      # kW x h x gCO2/kWh = grams
    return total_g / 1000


def risk_label(chance: float) -> str:
    if chance <= 0:
        return "None"
    return "Low" if chance <= LOW_RISK_MAX else "Medium" if chance <= MEDIUM_RISK_MAX else "High"
