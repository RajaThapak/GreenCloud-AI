"""Forecasters answer: what will this price or carbon value be at time t?
The optimizer only calls spot_price / on_demand_price / carbon, so an ML forecaster
can replace BaselineForecaster later without touching any scoring code."""
from __future__ import annotations

from datetime import datetime

from .models import MarketSnapshot


def _seasonal(latest: float, latest_hour: int, profile: list | None, hour: int) -> float:
    """Latest value reshaped by the typical hour-of-day pattern (seasonal-adjusted persistence)."""
    if not profile:
        return latest
    base, target = profile[latest_hour], profile[hour]
    if not base or base <= 0 or target is None:
        return latest
    return latest * target / base


class BaselineForecaster:
    name = "baseline-seasonal-persistence"

    def __init__(self, market: MarketSnapshot):
        self.m = market

    def spot_price(self, region: str, instance: str, when: datetime) -> float | None:
        q = self.m.spot.get((region, instance))
        if q is None:
            return None
        return _seasonal(q.price, q.observed_at.hour, self.m.spot_profile.get((region, instance)), when.hour)

    def on_demand_price(self, region: str, instance: str) -> float | None:
        q = self.m.on_demand.get((region, instance))
        return None if q is None else q.price

    def carbon(self, region: str, when: datetime) -> float | None:
        c = self.m.carbon.get(region)
        if c is None:
            return None
        return _seasonal(c.g_per_kwh, c.observed_at.hour, self.m.carbon_profile.get(region), when.hour)
