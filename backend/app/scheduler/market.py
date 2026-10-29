"""Loads a MarketSnapshot from the tables your chunk 2 collectors fill."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.market import CarbonIntensityRecord as Carbon
from ..models.market import PricingSnapshot as Pricing
from ..models.market import SpotPriceHistory as Spot
from .config import LATEST_LOOKBACK_H, PROFILE_DAYS
from .models import CarbonReading, MarketSnapshot, Quote


def _profiles(rows) -> dict:
    out: dict = {}
    for key, hour, avg in rows:
        out.setdefault(key, [None] * 24)[int(hour)] = float(avg)
    return out


def load_market(session: Session, now: datetime) -> MarketSnapshot:
    since = now - timedelta(hours=LATEST_LOOKBACK_H)
    since_profile = now - timedelta(days=PROFILE_DAYS)

    # latest Spot price per availability zone, then the cheapest zone per region and instance
    rows = session.execute(
        select(Spot.region, Spot.availability_zone, Spot.instance_type, Spot.spot_price, Spot.observed_at)
        .where(Spot.observed_at >= since, Spot.observed_at <= now)
        .distinct(Spot.region, Spot.availability_zone, Spot.instance_type)
        .order_by(Spot.region, Spot.availability_zone, Spot.instance_type, Spot.observed_at.desc())).all()
    spot: dict = {}
    for region, _az, itype, price, ts in rows:
        k = (region, itype)
        if k not in spot or price < spot[k].price:
            spot[k] = Quote(float(price), ts)

    rows = session.execute(
        select(Pricing.region, Pricing.instance_type, Pricing.price, Pricing.fetched_at)
        .distinct(Pricing.region, Pricing.instance_type)
        .order_by(Pricing.region, Pricing.instance_type, Pricing.fetched_at.desc())).all()
    on_demand = {(r, i): Quote(float(p), ts) for r, i, p, ts in rows}

    rows = session.execute(
        select(Carbon.region, Carbon.intensity, Carbon.source, Carbon.observed_at)
        .where(Carbon.observed_at >= now - timedelta(hours=48), Carbon.observed_at <= now)).all()
    best: dict = {}
    for region, g, src, ts in rows:                 # prefer live readings, then the newest
        rank = (src == "electricitymaps", ts)
        if region not in best or rank > best[region][0]:
            best[region] = (rank, CarbonReading(float(g), ts, src))
    carbon = {r: v[1] for r, v in best.items()}

    hr = func.extract("hour", Spot.observed_at)
    spot_profile = _profiles(
        ((r, i), h, a) for r, i, h, a in session.execute(
            select(Spot.region, Spot.instance_type, hr, func.avg(Spot.spot_price))
            .where(Spot.observed_at >= since_profile).group_by(Spot.region, Spot.instance_type, hr)).all())

    chr_ = func.extract("hour", Carbon.observed_at)
    carbon_profile = _profiles(
        (r, h, a) for r, h, a in session.execute(
            select(Carbon.region, chr_, func.avg(Carbon.intensity))
            .where(Carbon.observed_at >= since_profile, Carbon.source == "electricitymaps")
            .group_by(Carbon.region, chr_)).all())

    return MarketSnapshot(spot=spot, on_demand=on_demand, carbon=carbon,
                          spot_profile=spot_profile, carbon_profile=carbon_profile)
