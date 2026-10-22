import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from ..config import settings
from ..db import SessionLocal
from ..models.market import CarbonIntensityRecord

log = logging.getLogger(__name__)

# Verify zone codes for your token (see the check below).
ZONE = {"eu-north-1": "SE", "eu-west-1": "IE", "ca-central-1": "CA-ON",
        "us-east-1": "US-MIDA-PJM", "ap-south-1": "IN-WE"}

# Yearly average gCO2/kWh per region. Fill from a published source and cite it.
STATIC: dict[str, float] = {}


def _utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _fetch_live(region: str):
    base = settings.electricitymaps_base_url.rstrip("/")
    r = httpx.get(
        f"{base}/carbon-intensity/latest",
        params={"zone": ZONE[region]},
        headers={"auth-token": settings.ELECTRICITYMAPS_TOKEN},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    intensity = float(data["carbonIntensity"])
    stamp = data.get("datetime")
    observed_at = (
        _utc_naive(datetime.fromisoformat(stamp.replace("Z", "+00:00")))
        if stamp else _now()
    )
    return intensity, "electricitymaps", observed_at


def fetch_carbon(region: str):
    """Return (intensity, source, observed_at), or None if no data is available."""
    if settings.ELECTRICITYMAPS_TOKEN and region in ZONE:
        try:
            return _fetch_live(region)
        except httpx.HTTPStatusError as e:
            log.warning("Carbon API returned %s for %s", e.response.status_code, region)
        except (httpx.HTTPError, KeyError, ValueError, TypeError):
            log.warning("Live carbon fetch failed for %s", region, exc_info=True)
    if region in STATIC:
        return STATIC[region], "static", _now()
    return None


def collect_carbon(region: str) -> int:
    """Fetch one reading and save it. Returns the number of rows written."""
    result = fetch_carbon(region)
    if result is None:
        log.warning("No carbon data for %s", region)
        return 0
    intensity, source, observed_at = result
    with SessionLocal.begin() as s:
        exists = s.scalar(
            select(CarbonIntensityRecord.id).where(
                CarbonIntensityRecord.region == region,
                CarbonIntensityRecord.source == source,
                CarbonIntensityRecord.observed_at == observed_at,
            )
        )
        if exists:
            return 0
        s.add(CarbonIntensityRecord(
            region=region, intensity=intensity,
            source=source, observed_at=observed_at))
    return 1