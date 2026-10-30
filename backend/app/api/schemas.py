from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..scheduler.models import WorkloadSpec
from ..collectors.config import REGIONS as SUPPORTED_REGIONS


class AuthRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("A valid email address is required.")
        return normalized


class SignupRequest(AuthRequest):
    name: str = Field(min_length=1, max_length=200)


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class DashboardSummary(BaseModel):
    cost_saved: float
    carbon_avoided: float
    deadline_compliance: float
    active_workloads: int
    awaiting_approval: int


class PlanRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    image: str = ""
    vcpu: int = Field(default=1, ge=1)
    memory: float = Field(default=1, ge=1)
    gpu: str | int = 0
    duration: float = Field(gt=0)
    deadline: datetime
    priority: str = "Normal"
    opt_mode: str = Field(default="Balanced", alias="optMode")
    selected_regions: list[str] | None = None
    allowed_regions: list[str] | None = None
    checkpointing: bool = True

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def normalize_mode(self):
        self.opt_mode = self.opt_mode.capitalize()
        if self.opt_mode not in {"Cost", "Balanced", "Carbon"}:
            raise ValueError("optMode must be cost, balanced or carbon.")
        return self

    @model_validator(mode="after")
    def validate_regions(self):
        if self.selected_regions is not None:
            if not self.selected_regions:
                raise ValueError("selected_regions must contain at least one region.")
            if len(self.selected_regions) != len(set(self.selected_regions)):
                raise ValueError("selected_regions must not contain duplicates.")
            unsupported = sorted(set(self.selected_regions) - set(SUPPORTED_REGIONS))
            if unsupported:
                raise ValueError(
                    f"Unsupported selected_regions: {', '.join(unsupported)}."
                )
            if self.allowed_regions is not None and self.allowed_regions != self.selected_regions:
                raise ValueError("selected_regions and allowed_regions must match when both are provided.")
        elif self.allowed_regions is not None:
            if not self.allowed_regions:
                raise ValueError("allowed_regions must contain at least one region.")
            if len(self.allowed_regions) != len(set(self.allowed_regions)):
                raise ValueError("allowed_regions must not contain duplicates.")
            unsupported = sorted(set(self.allowed_regions) - set(SUPPORTED_REGIONS))
            if unsupported:
                raise ValueError(
                    f"Unsupported allowed_regions: {', '.join(unsupported)}."
                )
        return self

    def to_spec(self) -> WorkloadSpec:
        gpu_count = self.gpu
        if isinstance(gpu_count, str):
            try:
                gpu_count = int(gpu_count.split("x", 1)[0].strip())
            except ValueError:
                gpu_count = 0
        return WorkloadSpec(
            name=self.name,
            duration_h=self.duration,
            deadline=self.deadline.replace(tzinfo=None),
            mode=self.opt_mode,
            min_vcpu=self.vcpu,
            min_memory_gb=self.memory,
            min_gpus=gpu_count,
            allowed_regions=self.selected_regions or self.allowed_regions,
            checkpointing=self.checkpointing,
        )


class PlanResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    plan_id: int
    best: dict
    alternatives: list[dict]
    reasons: list[str]
    warnings: list[str]
    on_demand_cost: float | None = None
    run_now_carbon_kg: float | None = None
    relaxation_level: int
    inputs: dict


class PlanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workload_name: str
    mode: str
    created_at: datetime
    region: str
    instance_type: str
    purchase_type: str
    start_time: datetime
    est_cost: float
    est_carbon_kg: float
    result: dict


class WorkloadResponse(BaseModel):
    id: int
    name: str
    image: str
    status: str
    mode: str
    deadline: datetime
    duration: float
    vcpu: int
    memory: float
    gpu: int
    progress: float
    est_cost: float | None
    est_carbon: float | None
    actual_cost: float
    actual_carbon: float
    started_at: datetime | None
    finished_at: datetime | None
    failure_reason: str | None


class SettingsResponse(BaseModel):
    aws_access_key_id: str = ""
    electricitymaps_token: str = ""
    enabled_regions: list[str] = []
    default_mode: str = "cost"
    notify_email: bool = True
    notify_slack: bool = False
    slack_webhook: str = ""
    max_retries: int = 2
    spot_buffer: float = 1


class SettingsUpdate(BaseModel):
    aws_access_key_id: str | None = None
    electricitymaps_token: str | None = None
    enabled_regions: list[str] | None = None
    default_mode: str | None = None
    notify_email: bool | None = None
    notify_slack: bool | None = None
    slack_webhook: str | None = None
    max_retries: int | None = Field(default=None, ge=0, le=5)
    spot_buffer: float | None = Field(default=None, ge=0, le=12)
