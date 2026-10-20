import logging
from datetime import datetime, timezone

import httpx

from ..config import settings
from ..db import SessionLocal
from ..models.market import CarbonIntensityRecord

log = logging.getLogger(__name__)

ZONE = {"eu-north-1": "SE", "eu-west-1": "IE", "ca-central-1": "CA-ON",
        "us-east-1": "US-MIDA-PJM", "ap-south-1": "IN-WE"}  # verify codes in provider docs

# Yearly average gCO2/kWh per region. Fill from a published source and cite it.
STATIC: dict[str, float] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fetch_carbon(region: str):
    """Return (intensity, source, observed_at), or None if no data is available."""
    if settings.electricitymaps_token and region in ZONE:
        try:
            r = httpx.get(
                "https://api.electricitymap.org/v3/carbon-intensity/latest",
                params={"zone": ZONE[region]},
                headers={"auth-token": settings.electricitymaps_token},
                timeout=10,
            )
            r.raise_for_status()
            return float(r.json()["carbonIntensity"]), "electricitymaps", _now()
        except (httpx.HTTPError, KeyError, ValueError):
            log.warning("Live carbon fetch failed for %s, using fallback", region)
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
        s.add(CarbonIntensityRecord(
            region=region, intensity=intensity,
            source=source, observed_at=observed_at))
    return 1