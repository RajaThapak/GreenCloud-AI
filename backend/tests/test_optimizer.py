from datetime import datetime, timedelta

import pytest

from app.scheduler import NoEligibleInstance, NoFeasiblePlan, SchedulerError, WorkloadSpec, optimize
from app.scheduler.models import CarbonReading, MarketSnapshot, Quote

NOW = datetime(2026, 10, 26, 10, 0)
INST = "g5.xlarge"


def market(spot=None, od=None, carbon=None, **kw):
    q = lambda p: Quote(p, NOW)
    spot = {(r, INST): q(p) for r, p in (spot or {}).items()}
    od = {(r, INST): q(p) for r, p in (od or {}).items()}
    carbon = {r: CarbonReading(g, NOW, "electricitymaps") for r, g in (carbon or {}).items()}
    return MarketSnapshot(spot=spot, on_demand=od, carbon=carbon, **kw)


def three():
    return market(
        spot={"us-east-2": 0.40, "eu-north-1": 0.48, "ca-central-1": 0.52},
        od={"us-east-2": 1.0, "eu-north-1": 1.0, "ca-central-1": 1.0, "us-east-1": 1.0},
        carbon={"us-east-2": 400, "eu-north-1": 30, "ca-central-1": 120, "us-east-1": 380},
    )


def spec(mode="Balanced", hours_to_deadline=30, duration=6, **kw):
    return WorkloadSpec("job", duration, NOW + timedelta(hours=hours_to_deadline), mode,
                        min_vcpu=4, min_memory_gb=16, min_gpus=1, **kw)


@pytest.mark.parametrize("mode,region", [("Cost", "us-east-2"), ("Carbon", "eu-north-1"), ("Balanced", "eu-north-1")])
def test_each_mode_picks_expected_region(mode, region):
    r = optimize(spec(mode), three(), NOW)
    assert r.best.region == region
    assert r.best.start == NOW          # flat forecast: no reason to wait


def test_never_returns_a_plan_that_misses_the_deadline():
    r = optimize(spec(hours_to_deadline=12), three(), NOW)
    for c in [r.best, *r.alternatives]:
        assert c.finish <= NOW + timedelta(hours=12)
        assert c.start <= NOW + timedelta(hours=12 - 6 * 1.2)


def test_exact_buffer_boundary_allows_only_now():
    r = optimize(spec(hours_to_deadline=7.2), three(), NOW)
    assert r.best.start == NOW and r.relaxation_level == 0


def test_tight_deadline_relaxes_to_on_demand_with_warning():
    r = optimize(spec(hours_to_deadline=6.5), three(), NOW)
    assert r.relaxation_level == 1
    assert r.best.purchase == "On-demand" and r.best.risk_chance == 0
    assert any("on-demand" in w for w in r.warnings)


def test_impossible_deadline_raises_with_earliest_finish():
    with pytest.raises(NoFeasiblePlan) as e:
        optimize(spec(hours_to_deadline=5), three(), NOW)
    assert e.value.earliest_finish == NOW + timedelta(hours=6)


def test_impossible_requirements_raise():
    s = spec()
    s.min_gpus = 4
    with pytest.raises(NoEligibleInstance):
        optimize(s, three(), NOW)


def test_bad_inputs_raise_clear_errors():
    with pytest.raises(SchedulerError):
        optimize(spec(mode="Fastest"), three(), NOW)
    with pytest.raises(SchedulerError):
        optimize(spec(hours_to_deadline=-1), three(), NOW)
    with pytest.raises(SchedulerError):
        optimize(spec(), MarketSnapshot({}, {}, {}), NOW)


def test_missing_spot_price_falls_back_to_on_demand():
    m = three()
    m.on_demand[("ap-south-1", INST)] = Quote(1.0, NOW)
    m.carbon["ap-south-1"] = CarbonReading(10, NOW, "electricitymaps")
    r = optimize(spec("Carbon"), m, NOW)
    assert r.best.region == "ap-south-1" and r.best.purchase == "On-demand"
    assert any("No Spot price" in w for w in r.warnings)


def test_region_without_carbon_data_is_skipped_with_warning():
    m = three()
    del m.carbon["us-east-2"]
    r = optimize(spec("Cost"), m, NOW)
    assert r.best.region != "us-east-2"
    assert any("us-east-2" in w for w in r.warnings)


def test_all_equal_values_do_not_crash():
    m = market(spot={"a": 0.5, "b": 0.5}, od={"a": 1, "b": 1}, carbon={"a": 100, "b": 100})
    r = optimize(spec(), m, NOW)
    assert r.best.score == 0 and r.best.region == "a"       # tie broken by name


def test_result_is_deterministic():
    assert optimize(spec(), three(), NOW).to_dict() == optimize(spec(), three(), NOW).to_dict()


def test_alternatives_are_distinct_regions():
    r = optimize(spec(), three(), NOW)
    regions = [r.best.region] + [a.region for a in r.alternatives]
    assert len(regions) == len(set(regions)) == 3


def test_no_checkpoint_job_gets_higher_risk_adjusted_cost():
    a = optimize(spec(), three(), NOW).best
    b = optimize(spec(checkpointing=False), three(), NOW).best
    assert b.risk_adj_cost > a.risk_adj_cost and b.cost == a.cost


def test_hourly_pattern_moves_start_to_the_cleaner_hour():
    profile = [400.0] * 24
    profile[13] = 100.0                                    # cleanest hour of the day
    m = market(spot={"eu-north-1": 0.5}, od={"eu-north-1": 1.0}, carbon={"eu-north-1": 400},
               carbon_profile={"eu-north-1": profile})
    r = optimize(spec("Carbon", hours_to_deadline=24, duration=1), m, NOW)
    assert r.best.start.hour == 13
    assert any("Starting at" in x for x in r.reasons)


def test_stale_data_produces_warnings():
    m = three()
    m.carbon["eu-north-1"] = CarbonReading(30, NOW - timedelta(hours=10), "electricitymaps")
    r = optimize(spec("Carbon"), m, NOW)
    assert any("Carbon data" in w for w in r.warnings)


def test_reasons_cover_cost_carbon_deadline_and_risk():
    text = " ".join(optimize(spec(), three(), NOW).reasons)
    for word in ["Estimated cost", "emissions", "before your deadline", "Interruption risk"]:
        assert word in text


def test_savings_baselines_present():
    r = optimize(spec(), three(), NOW)
    assert r.on_demand_cost == pytest.approx(6.0) and r.run_now_carbon_kg > r.best.carbon_kg
