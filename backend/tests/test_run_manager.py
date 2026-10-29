from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.execution.datatypes import LaunchRequest, Placement
from app.execution.fake import FakeCloud
from app.execution.manager import RunManager
from app.models.execution import ExecutionRun, RunAttempt

NOW = datetime(2026, 10, 26, 10, 0)
SPOT_A = Placement("eu-north-1", "g5.xlarge", "Spot", 0.5, 1.0)
SPOT_B = Placement("us-east-2", "g5.xlarge", "Spot", 0.4, 2.0)
OD = Placement("eu-north-1", "g5.xlarge", "On-demand", 1.0, 1.0)


class Stub:
    """Stands in for the optimizer: tries two Spot options, then on-demand."""
    def __init__(self):
        self.calls = []

    def __call__(self, run, remaining_h, pref, now):
        self.calls.append((pref, round(remaining_h, 4)))
        return [SPOT_A, SPOT_B, OD] if pref == "Spot" else [OD]


@pytest.fixture
def env():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine)
    cloud, stub, events = FakeCloud(NOW), Stub(), []
    mgr = RunManager(session, cloud, stub, clock=lambda: cloud.now, notify=lambda r, ev, m: events.append(ev))
    return SimpleNamespace(s=session, cloud=cloud, stub=stub, events=events, mgr=mgr)


def make_run(env, duration=6, deadline_h=30, checkpointing=True):
    run = ExecutionRun(workload_name="job", image="img", deadline=NOW + timedelta(hours=deadline_h),
                       duration_h=duration, checkpointing=checkpointing)
    env.s.add(run)
    env.s.flush()
    return run


def attempts(env, run):
    return list(env.s.scalars(select(RunAttempt).where(RunAttempt.run_id == run.id).order_by(RunAttempt.number)))


def active_id(env, run):
    return env.mgr._active(run).instance_id


def interrupt(env, run, after_h):
    env.cloud.interrupt_in(active_id(env, run), after_h)
    env.cloud.advance(after_h)
    env.mgr.tick(run.id)


def test_job_without_interruptions_completes(env):
    run = make_run(env)
    env.mgr.start(run.id)
    assert run.status == "Running"
    env.cloud.advance(6)
    env.mgr.tick(run.id)
    assert run.status == "Completed" and len(attempts(env, run)) == 1
    assert run.actual_cost == pytest.approx(3.0)


def test_one_interruption_resumes_from_checkpoint_and_costs_add_up(env):
    run = make_run(env)
    env.mgr.start(run.id)
    interrupt(env, run, 2.0)
    a1, a2 = attempts(env, run)
    assert a1.end_reason == "interrupted" and a2.purchase == "Spot"
    assert a2.start_progress == pytest.approx(1 / 3)
    assert env.stub.calls[-1] == ("Spot", 4.0)                  # only the remaining 4 hours are planned
    assert a1.wasted_h == pytest.approx(0, abs=1e-6)            # checkpoint was current
    env.cloud.advance(4.0)
    env.mgr.tick(run.id)
    assert run.status == "Recovered" and run.interruptions == 1 and run.spot_relaunches == 1
    assert run.actual_cost == pytest.approx(3.0)
    assert sum(a.cost for a in attempts(env, run)) == pytest.approx(run.actual_cost)
    assert {"interrupted", "recovered", "completed"} <= set(env.events)


def test_spot_retries_exhausted_then_on_demand(env):
    run = make_run(env)
    env.mgr.start(run.id)
    for _ in range(3):
        interrupt(env, run, 1.0)
    assert [a.purchase for a in attempts(env, run)] == ["Spot", "Spot", "Spot", "On-demand"]
    assert [c[0] for c in env.stub.calls] == ["Spot", "Spot", "Spot", "On-demand"]


def test_tight_deadline_goes_straight_to_on_demand(env):
    run = make_run(env, deadline_h=7)
    env.mgr.start(run.id)
    interrupt(env, run, 1.0)
    assert attempts(env, run)[1].purchase == "On-demand" and not run.deadline_at_risk


def test_impossible_deadline_marks_at_risk_but_keeps_running(env):
    run = make_run(env, deadline_h=5)
    env.mgr.start(run.id)
    interrupt(env, run, 1.0)
    assert run.deadline_at_risk and run.status == "Running" and "at_risk" in env.events
    assert attempts(env, run)[1].purchase == "On-demand"


def test_capacity_error_falls_back_to_next_option(env):
    env.cloud.fail_launch("eu-north-1", "g5.xlarge", "Spot")
    run = make_run(env)
    env.mgr.start(run.id)
    assert attempts(env, run)[0].region == "us-east-2"


def test_no_capacity_anywhere_waits_then_recovers(env):
    for p in (SPOT_A, SPOT_B, OD):
        env.cloud.fail_launch(p.region, p.instance, p.purchase)
    run = make_run(env)
    env.mgr.start(run.id)
    assert run.status == "Recovering" and attempts(env, run) == []
    env.cloud.clear_failures()
    env.mgr.tick(run.id)
    assert run.status == "Running" and len(attempts(env, run)) == 1


def test_persistent_capacity_failure_eventually_fails(env):
    for p in (SPOT_A, SPOT_B, OD):
        env.cloud.fail_launch(p.region, p.instance, p.purchase)
    run = make_run(env)
    env.mgr.start(run.id)
    for _ in range(10):
        env.mgr.tick(run.id)
    assert run.status == "Failed" and "capacity" in run.failure_reason


def test_job_without_checkpoints_restarts_from_zero(env):
    run = make_run(env, checkpointing=False)
    env.mgr.start(run.id)
    interrupt(env, run, 2.0)
    a1, a2 = attempts(env, run)
    assert env.stub.calls[-1] == ("Spot", 6.0) and a2.start_progress == 0
    assert a1.wasted_h == pytest.approx(2.0)


def test_repeated_ticks_do_not_launch_twice(env):
    run = make_run(env)
    env.mgr.start(run.id)
    interrupt(env, run, 2.0)
    env.mgr.tick(run.id)
    env.mgr.tick(run.id)
    assert len(attempts(env, run)) == 2 and len(env.cloud.launch_log) == 2


def test_same_launch_token_returns_same_instance(env):
    req = LaunchRequest(1, 1, "eu-north-1", "g5.xlarge", "Spot", 0, 6, True, "img", "tok")
    assert env.cloud.launch(req) == env.cloud.launch(req) and len(env.cloud.instances) == 1


def test_silent_instance_is_treated_as_lost(env):
    run = make_run(env)
    env.mgr.start(run.id)
    old = active_id(env, run)
    env.cloud.make_silent(old)
    env.cloud.advance(0.5)
    env.mgr.tick(run.id)
    a1, a2 = attempts(env, run)
    assert a1.end_reason == "lost" and a2.number == 2
    assert env.cloud.describe(old).state == "terminated"


def test_job_error_is_not_retried(env):
    run = make_run(env)
    env.mgr.start(run.id)
    env.cloud.fail_job(active_id(env, run))
    env.mgr.tick(run.id)
    assert run.status == "Failed" and "not retried" in run.failure_reason and len(attempts(env, run)) == 1


def test_gives_up_after_max_attempts(env):
    run = make_run(env)
    env.mgr.start(run.id)
    for _ in range(4):
        interrupt(env, run, 1.0)
    assert run.status == "Failed" and "attempts" in run.failure_reason


def test_cancel_terminates_the_instance(env):
    run = make_run(env)
    env.mgr.start(run.id)
    iid = active_id(env, run)
    env.mgr.cancel(run.id)
    assert run.status == "Cancelled" and env.cloud.describe(iid).state == "terminated"
    assert attempts(env, run)[0].end_reason == "cancelled"


def test_reaper_kills_orphans_but_not_active_instances(env):
    run = make_run(env)
    env.mgr.start(run.id)
    env.cloud.launch(LaunchRequest(999, 1, "us-east-2", "g5.xlarge", "Spot", 0, 6, True, "img", "orphan"))
    env.cloud.advance(0.2)                                       # past the grace period
    assert env.mgr.reap() == 1
    assert env.cloud.describe(active_id(env, run)).state == "running"


def test_reaper_spares_brand_new_instances(env):
    env.cloud.launch(LaunchRequest(999, 1, "us-east-2", "g5.xlarge", "Spot", 0, 6, True, "img", "new"))
    assert env.mgr.reap() == 0


def test_interruption_notice_is_reported_once(env):
    run = make_run(env)
    env.mgr.start(run.id)
    env.cloud.interrupt_in(active_id(env, run), 1.0)
    env.cloud.advance(1.0 - 1 / 60)                              # one minute before reclaim
    env.mgr.tick(run.id)
    env.mgr.tick(run.id)
    assert env.events.count("warning") == 1


def test_optimizer_placements_use_the_chunk4_optimizer(monkeypatch):
    from app.execution import placement
    from app.scheduler.models import CarbonReading, MarketSnapshot, Quote

    q = lambda p: Quote(p, NOW)
    market = MarketSnapshot(
        spot={(r, "g5.xlarge"): q(p) for r, p in {"us-east-2": 0.4, "eu-north-1": 0.48, "ca-central-1": 0.52}.items()},
        on_demand={(r, "g5.xlarge"): q(1.0) for r in ("us-east-2", "eu-north-1", "ca-central-1")},
        carbon={r: CarbonReading(g, NOW, "electricitymaps") for r, g in
                {"us-east-2": 400, "eu-north-1": 30, "ca-central-1": 120}.items()})
    monkeypatch.setattr(placement, "load_market", lambda session, now: market)
    run = ExecutionRun(id=1, workload_name="job", deadline=NOW + timedelta(hours=30), duration_h=6, mode="Balanced",
                       min_vcpu=4, min_memory_gb=16, min_gpus=1, allowed_regions=None, checkpointing=True)
    op = placement.OptimizerPlacements(session=None)

    spot = op(run, 4.0, "Spot", NOW)
    assert spot[0].purchase == "Spot" and spot[0].region == "eu-north-1" and spot[0].price_per_h > 0
    assert all(p.purchase == "On-demand" for p in op(run, 4.0, "On-demand", NOW))
    run.deadline = NOW + timedelta(hours=1)                      # impossible: the last resort must still exist
    assert op(run, 4.0, "Spot", NOW)[-1].purchase == "On-demand"
