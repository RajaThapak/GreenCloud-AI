from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime

from .config import INTERRUPTION_BY_FAMILY, WATTS_PER_GPU, WATTS_PER_VCPU


class SchedulerError(Exception):
    """Base class: every error here has a message safe to show the user."""


class NoEligibleInstance(SchedulerError):
    pass


class NoFeasiblePlan(SchedulerError):
    def __init__(self, message: str, earliest_finish: datetime | None = None):
        super().__init__(message)
        self.earliest_finish = earliest_finish


@dataclass(frozen=True)
class InstanceSpec:
    name: str
    vcpu: int
    memory_gb: float
    gpus: int = 0

    @property
    def family(self) -> str:
        return self.name.split(".")[0]

    @property
    def power_kw(self) -> float:
        return (self.vcpu * WATTS_PER_VCPU + self.gpus * WATTS_PER_GPU) / 1000


@dataclass
class WorkloadSpec:
    name: str
    duration_h: float
    deadline: datetime                      # naive UTC
    mode: str = "Balanced"                  # Cost | Balanced | Carbon
    min_vcpu: int = 1
    min_memory_gb: float = 1
    min_gpus: int = 0
    allowed_regions: list[str] | None = None
    checkpointing: bool = True


@dataclass
class Quote:
    price: float                            # USD per hour
    observed_at: datetime


@dataclass
class CarbonReading:
    g_per_kwh: float
    observed_at: datetime
    source: str


@dataclass
class MarketSnapshot:
    spot: dict[tuple[str, str], Quote]
    on_demand: dict[tuple[str, str], Quote]
    carbon: dict[str, CarbonReading]
    spot_profile: dict[tuple[str, str], list] = field(default_factory=dict)   # 24 values per (region, instance)
    carbon_profile: dict[str, list] = field(default_factory=dict)             # 24 values per region
    interruption: dict[str, float] = field(default_factory=lambda: dict(INTERRUPTION_BY_FAMILY))


@dataclass
class Candidate:
    region: str
    instance: str
    purchase: str                           # Spot | On-demand
    start: datetime
    finish: datetime
    cost: float
    risk_adj_cost: float
    carbon_kg: float
    risk_chance: float
    risk_label: str
    score: float = 0.0


@dataclass
class PlanResult:
    best: Candidate
    alternatives: list[Candidate]
    reasons: list[str]
    warnings: list[str]
    on_demand_cost: float | None
    run_now_carbon_kg: float | None
    relaxation_level: int
    inputs: dict

    def to_dict(self) -> dict:
        return _plain(self)


def _plain(x):
    if isinstance(x, datetime):
        return x.isoformat()
    if is_dataclass(x):
        return {f.name: _plain(getattr(x, f.name)) for f in fields(x)}
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [_plain(v) for v in x]
    return x
