from datetime import datetime, timedelta

from app.execution.recovery import RecoveryInput, decide

NOW = datetime(2026, 10, 26, 10, 0)


def inp(**kw):
    base = dict(now=NOW, deadline=NOW + timedelta(hours=30), duration_h=6, progress=0.0,
                spot_relaunches=0, total_attempts=1)
    return RecoveryInput(**{**base, **kw})


def test_plenty_of_slack_relaunches_on_spot():
    d = decide(inp())
    assert d.action == "relaunch_spot" and not d.at_risk


def test_spot_retries_used_up_goes_on_demand():
    d = decide(inp(spot_relaunches=2, total_attempts=3))
    assert d.action == "launch_on_demand" and not d.at_risk


def test_tight_deadline_goes_on_demand_without_being_at_risk():
    # 5 h of work left plus 0.1 h restart = 5.1 h; 6 h left is enough once but not with the 20% buffer
    d = decide(inp(deadline=NOW + timedelta(hours=6), progress=1 / 6))
    assert d.action == "launch_on_demand" and not d.at_risk and d.slack_h > 0


def test_impossible_deadline_is_flagged_but_still_runs():
    d = decide(inp(deadline=NOW + timedelta(hours=4), progress=1 / 6))
    assert d.action == "launch_on_demand" and d.at_risk and d.slack_h < 0


def test_too_many_attempts_fails():
    d = decide(inp(total_attempts=4))
    assert d.action == "fail" and "4 attempts" in d.reason


def test_checkpoint_progress_reduces_remaining_work():
    assert decide(inp(progress=0.5)).remaining_h == 3.0


def test_out_of_range_progress_is_clamped():
    assert decide(inp(progress=1.5)).remaining_h == 0.0
    assert decide(inp(progress=-1)).remaining_h == 6.0
