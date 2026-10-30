from datetime import datetime, timedelta

import pytest

from app.api.schemas import PlanRequest
from app.collectors.config import REGIONS
from app.scheduler import SchedulerError, WorkloadSpec, optimize
from app.scheduler.models import CarbonReading, MarketSnapshot, Quote


NOW = datetime(2026, 10, 26, 10, 0)
INSTANCE = "g5.xlarge"


def market():
    quote = lambda price: Quote(price, NOW)
    regions = {
        "us-east-1": 0.40,
        "us-east-2": 0.45,
        "eu-north-1": 0.50,
        "eu-west-1": 0.55,
        "ca-central-1": 0.60,
        "ap-south-1": 0.65,
    }
    return MarketSnapshot(
        spot={(region, INSTANCE): quote(price) for region, price in regions.items()},
        on_demand={(region, INSTANCE): quote(1.0) for region in regions},
        carbon={
            region: CarbonReading(100 + index * 10, NOW, "electricitymaps")
            for index, region in enumerate(regions)
        },
    )


def workload(**kwargs):
    return WorkloadSpec(
        "region-filtered-job",
        duration_h=2,
        deadline=NOW + timedelta(hours=12),
        min_vcpu=4,
        min_memory_gb=16,
        min_gpus=1,
        **kwargs,
    )


def test_selected_regions_limit_best_and_alternatives():
    selected = ["us-east-2", "eu-north-1", "ap-south-1"]
    result = optimize(workload(allowed_regions=selected), market(), NOW)

    recommended = {result.best.region, *(candidate.region for candidate in result.alternatives)}
    assert recommended <= set(selected)


def test_missing_carbon_data_is_explained_without_using_unselected_region():
    selected = ["eu-north-1", "ap-south-1"]
    data = market()
    del data.carbon["ap-south-1"]

    result = optimize(workload(allowed_regions=selected), data, NOW)

    assert result.best.region == "eu-north-1"
    assert all(candidate.region in selected for candidate in result.alternatives)
    assert any("ap-south-1" in warning and "carbon" in warning for warning in result.warnings)


def test_stale_selected_region_data_is_reported():
    selected = ["eu-north-1", "ap-south-1"]
    data = market()
    data.carbon["ap-south-1"] = CarbonReading(
        150, NOW - timedelta(hours=4), "electricitymaps"
    )

    result = optimize(workload(allowed_regions=selected), data, NOW)

    assert result.best.region in selected
    assert all(candidate.region in selected for candidate in result.alternatives)
    assert any("ap-south-1" in warning and "old" in warning for warning in result.warnings)


def test_selected_region_without_pricing_is_reported():
    selected = ["eu-north-1", "ap-south-1"]
    data = market()
    data.spot.pop(("ap-south-1", INSTANCE))
    data.on_demand.pop(("ap-south-1", INSTANCE))

    result = optimize(workload(allowed_regions=selected), data, NOW)

    assert result.best.region == "eu-north-1"
    assert all(candidate.region in selected for candidate in result.alternatives)
    assert any("ap-south-1" in warning and "pricing" in warning for warning in result.warnings)


def test_no_market_data_for_selected_regions_raises():
    with pytest.raises(SchedulerError, match="No price data is available"):
        optimize(
            workload(allowed_regions=["ap-south-1"]),
            MarketSnapshot({}, {}, {}),
            NOW,
        )


def test_selected_region_validation_rejects_empty_unsupported_and_duplicates():
    base = {
        "name": "job",
        "vcpu": 1,
        "memory": 1,
        "gpu": 0,
        "duration": 1,
        "deadline": NOW,
    }

    with pytest.raises(ValueError, match="at least one"):
        PlanRequest(**base, selected_regions=[])
    with pytest.raises(ValueError, match="Unsupported"):
        PlanRequest(**base, selected_regions=["not-a-region"])
    with pytest.raises(ValueError, match="duplicates"):
        PlanRequest(**base, selected_regions=["us-east-1", "us-east-1"])


def test_region_validation_uses_collector_canonical_regions():
    assert REGIONS == [
        "us-east-1",
        "us-east-2",
        "eu-north-1",
        "eu-west-1",
        "ca-central-1",
        "ap-south-1",
    ]
