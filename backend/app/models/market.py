# app/models/market.py
from datetime import datetime
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base

class SpotPriceHistory(Base):
    __tablename__ = "spot_price_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    region: Mapped[str] = mapped_column(String(20), index=True)
    availability_zone: Mapped[str] = mapped_column(String(30))
    instance_type: Mapped[str] = mapped_column(String(30), index=True)
    spot_price: Mapped[float]
    observed_at: Mapped[datetime] = mapped_column(index=True)
    __table_args__ = (UniqueConstraint("region", "availability_zone",
                      "instance_type", "observed_at"),)

class PricingSnapshot(Base):
    __tablename__ = "pricing_snapshot"
    id: Mapped[int] = mapped_column(primary_key=True)
    region: Mapped[str] = mapped_column(String(20))
    instance_type: Mapped[str] = mapped_column(String(30))
    price: Mapped[float]            # on-demand USD/hour
    fetched_at: Mapped[datetime]

class CarbonIntensityRecord(Base):
    __tablename__ = "carbon_intensity_record"
    id: Mapped[int] = mapped_column(primary_key=True)
    region: Mapped[str] = mapped_column(String(20), index=True)
    intensity: Mapped[float]        # gCO2/kWh
    source: Mapped[str] = mapped_column(String(30))   # "electricitymaps" or "static"
    observed_at: Mapped[datetime] = mapped_column(index=True)