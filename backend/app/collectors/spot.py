# app/collectors/spot.py
from datetime import datetime, timedelta, timezone
import boto3
from sqlalchemy.dialects.postgresql import insert
from ..db import SessionLocal
from ..models.market import SpotPriceHistory
from .config import INSTANCE_TYPES

def collect_spot(region: str, hours: int = 6) -> int:
    ec2 = boto3.client("ec2", region_name=region)
    pages = ec2.get_paginator("describe_spot_price_history").paginate(
        InstanceTypes=INSTANCE_TYPES,
        ProductDescriptions=["Linux/UNIX"],
        StartTime=datetime.now(timezone.utc) - timedelta(hours=hours),
    )
    rows = [
        {"region": region, "availability_zone": p["AvailabilityZone"],
         "instance_type": p["InstanceType"], "spot_price": float(p["SpotPrice"]),
         "observed_at": p["Timestamp"].replace(tzinfo=None)}
        for page in pages for p in page["SpotPriceHistory"]
    ]
    if rows:
        with SessionLocal.begin() as s:
            s.execute(insert(SpotPriceHistory).values(rows).on_conflict_do_nothing())
    return len(rows)