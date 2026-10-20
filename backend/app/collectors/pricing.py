from datetime import datetime, timezone
from ..db import SessionLocal
from ..models.market import PricingSnapshot
from .config import INSTANCE_TYPES

def collect_pricing(region: str) -> int:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    count = 0
    with SessionLocal.begin() as s:
        for itype in INSTANCE_TYPES:
            price = fetch_on_demand(region, itype)
            if price is None:
                continue
            s.add(PricingSnapshot(region=region, instance_type=itype,
                                  price=price, fetched_at=now))
            count += 1
    return count