from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class CapacityError(Exception):
    """The cloud has no capacity (or quota) for this instance type right now."""


@dataclass(frozen=True)
class Placement:
    region: str
    instance: str
    purchase: str              # Spot | On-demand
    price_per_h: float
    kg_per_h: float


@dataclass(frozen=True)
class LaunchRequest:
    run_id: int
    attempt_number: int
    region: str
    instance_type: str
    purchase: str
    start_progress: float      # 0..1, resume point from the last checkpoint
    total_duration_h: float
    checkpointing: bool
    image: str
    token: str                 # idempotency token: the same token never launches twice


@dataclass(frozen=True)
class InstanceInfo:
    state: str                 # running | finished | failed | interrupted | terminated | missing
    ended_at: datetime | None = None
