import json
import logging
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import select

from ..db import SessionLocal
from ..models.market import PricingSnapshot
from .config import INSTANCE_TYPES

log = logging.getLogger(__name__)

# The Pricing API identifies regions by display name.
LOCATION = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "eu-north-1": "EU (Stockholm)",
    "eu-west-1": "EU (Ireland)",
    "ca-central-1": "Canada (Central)",
    "ap-south-1": "Asia Pacific (Mumbai)",
}

_client = None


def _pricing_client():
    # The Pricing API is only served from a few regions; us-east-1 works for all prices.
    global _client
    if _client is None:
        _client = boto3.client("pricing", region_name="us-east-1")
    return _client


def fetch_on_demand(region: str, instance_type: str) -> float | None:
    """On-demand Linux price in USD per hour, or None if unavailable."""
    if region not in LOCATION:
        log.warning("No pricing location mapped for %s", region)
        return None
    filters = [
        {"Type": "TERM_MATCH", "Field": f, "Value": v}
        for f, v in [
            ("location", LOCATION[region]),
            ("instanceType", instance_type),
            ("operatingSystem", "Linux"),
            ("tenancy", "Shared"),
            ("preInstalledSw", "NA"),
            ("capacitystatus", "Used"),
        ]
    ]
    try:
        resp = _pricing_client().get_products(ServiceCode="AmazonEC2", Filters=filters)
        if not resp["PriceList"]:
            log.warning("No price found for %s %s (location=%r)",
                        region, instance_type, LOCATION[region])
            return None
        terms = json.loads(resp["PriceList"][0])["terms"]["OnDemand"]
        dim = next(iter(next(iter(terms.values()))["priceDimensions"].values()))
        return float(dim["pricePerUnit"]["USD"])
    except (BotoCoreError, ClientError, KeyError, StopIteration, ValueError):
        log.warning("Price lookup failed for %s %s", region, instance_type, exc_info=True)
        return None


def collect_pricing(region: str) -> int:
    """Collect on-demand pricing for a region and return the number of new entries added."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(hours=12)

    # 1) Fetch from AWS first, with no database transaction open.
    prices = {}
    for itype in INSTANCE_TYPES:
        price = fetch_on_demand(region, itype)
        if price is not None:
            prices[itype] = price

    # 2) Then write quickly, skipping anything saved in the last 12 hours.
    count = 0
    with SessionLocal.begin() as s:
        for itype, price in prices.items():
            recent = s.scalar(
                select(PricingSnapshot.id).where(
                    PricingSnapshot.region == region,
                    PricingSnapshot.instance_type == itype,
                    PricingSnapshot.fetched_at >= cutoff,
                ).limit(1)
            )
            if recent:
                continue
            s.add(PricingSnapshot(region=region, instance_type=itype,
                                  price=price, fetched_at=now))
            count += 1
    return count