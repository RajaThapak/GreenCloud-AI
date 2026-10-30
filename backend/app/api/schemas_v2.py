from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator
from pydantic.alias_generators import to_camel

CAMEL = False
Mode = Literal["Cost", "Balanced", "Carbon"]
WType = Literal["ML training", "Batch / ETL", "Rendering", "Simulation"]
EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def _utc(value: datetime) -> str:
    value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


UtcDT = Annotated[datetime, PlainSerializer(_utc, return_type=str)]


class Api(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel if CAMEL else None)


class RegisterIn(Api):
    email: str = Field(pattern=EMAIL)
    password: str = Field(min_length=8)
    org_name: str | None = None


class LoginIn(Api):
    email: str
    password: str


class CreateUserIn(Api):
    email: str = Field(pattern=EMAIL)
    password: str = Field(min_length=8)
    role: Literal["Admin", "User"] = "User"


class UserOut(Api):
    id: int
    email: str
    role: str
    org_id: int


class TokenOut(Api):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RequirementsIn(Api):
    workload_type: WType
    needs_gpu: bool = False


class WorkloadIn(Api):
    name: str = Field(min_length=1, max_length=200)
    image: str = Field(min_length=1, max_length=300)
    workload_type: WType = "ML training"
    duration_h: float = Field(gt=0, le=720)
    deadline: datetime
    mode: Mode = "Balanced"
    min_vcpu: int = Field(1, ge=1, le=192)
    min_memory_gb: float = Field(1, gt=0, le=2048)
    min_gpus: int = Field(0, ge=0, le=8)
    checkpointing: bool = True
    allowed_regions: list[str] | None = None

    @field_validator("deadline")
    @classmethod
    def future_deadline(cls, value: datetime) -> datetime:
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        if value <= datetime.now(timezone.utc).replace(tzinfo=None):
            raise ValueError("The deadline must be in the future.")
        return value


class ReplanIn(Api):
    mode: Mode


class CandidateOut(Api):
    region: str
    instance: str
    purchase: str
    start: UtcDT
    finish: UtcDT
    cost: float
    risk_adj_cost: float
    carbon_kg: float
    risk_chance: float
    risk_label: str
    score: float


class PlanOut(Api):
    best: CandidateOut
    alternatives: list[CandidateOut]
    reasons: list[str]
    warnings: list[str]
    on_demand_cost: float | None
    run_now_carbon_kg: float | None
    relaxation_level: int


class AttemptOut(Api):
    number: int
    region: str
    instance_type: str
    purchase: str
    started_at: UtcDT
    ended_at: UtcDT | None
    end_reason: str | None
    start_progress: float
    end_progress: float | None
    cost: float
    carbon_kg: float
    wasted_h: float


class RunOut(Api):
    id: int
    status: str
    progress: float
    interruptions: int
    spot_relaunches: int
    deadline_at_risk: bool
    actual_cost: float
    actual_carbon_kg: float
    wasted_h: float
    started_at: UtcDT | None
    finished_at: UtcDT | None
    failure_reason: str | None
    attempts: list[AttemptOut]


class WorkloadSummary(Api):
    id: int
    name: str
    mode: str
    status: str
    region: str | None
    instance_type: str | None
    est_cost: float | None
    actual_cost: float | None
    est_carbon_kg: float | None
    actual_carbon_kg: float | None
    deadline: UtcDT
    created_at: UtcDT


class WorkloadDetail(WorkloadSummary):
    image: str
    workload_type: str
    duration_h: float
    min_vcpu: int
    min_memory_gb: float
    min_gpus: int
    checkpointing: bool
    allowed_regions: list[str] | None
    plan: PlanOut | None
    run: RunOut | None


class MonthRow(Api):
    month: str
    label: str
    on_demand: float
    estimated: float
    actual: float


class ReportRow(MonthRow):
    variance_pct: float | None


class ReportOut(Api):
    rows: list[ReportRow]
    total_on_demand: float
    total_estimated: float
    total_actual: float
    saved: float
    saved_pct: float | None


class CarbonNow(Api):
    region: str
    g_per_kwh: float
    source: str
    observed_at: UtcDT


class DashboardOut(Api):
    cost_saved: float
    cost_saved_pct: float | None
    carbon_avoided_kg: float
    carbon_avoided_pct: float | None
    deadlines_met: int
    deadlines_total: int
    deadlines_met_pct: float | None
    active_workloads: int
    awaiting_approval: int
    months: list[MonthRow]
    carbon_now: list[CarbonNow]
    recent: list[WorkloadSummary]


class Freshness(Api):
    spot_latest: UtcDT | None
    pricing_latest: UtcDT | None
    carbon_latest: UtcDT | None
    spot_age_min: float | None
    pricing_age_min: float | None
    carbon_age_min: float | None


class SettingsIn(Api):
    budget: float = Field(gt=0)
    default_mode: Mode
    regions: list[str]


class SettingsOut(SettingsIn):
    aws_connected: bool
    aws_role_arn: str | None
    aws_external_id: str


class AwsVerifyIn(Api):
    role_arn: str


class AuditOut(Api):
    id: int
    user_email: str | None
    action: str
    target: str
    detail: dict | None
    created_at: UtcDT


class AdvanceIn(Api):
    hours: float = Field(gt=0, le=240)
