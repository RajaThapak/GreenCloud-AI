"""What to do after an interruption. A pure function: plain numbers in, a decision out."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..scheduler.config import DEADLINE_BUFFER
from .config import MAX_ATTEMPTS, MAX_SPOT_RETRIES, RESTART_OVERHEAD_H


@dataclass(frozen=True)
class RecoveryInput:
    now: datetime
    deadline: datetime
    duration_h: float
    progress: float            # 0..1 from the last checkpoint (0 if the job cannot checkpoint)
    spot_relaunches: int       # Spot relaunches already done after interruptions
    total_attempts: int        # every launch so far


@dataclass(frozen=True)
class Decision:
    action: str                # relaunch_spot | launch_on_demand | fail
    at_risk: bool              # even the best choice may miss the deadline
    remaining_h: float
    slack_h: float             # hours to spare after the remaining work (negative = already late)
    reason: str


def decide(i: RecoveryInput) -> Decision:
    progress = min(1.0, max(0.0, i.progress))
    remaining = i.duration_h * (1 - progress)
    need = remaining + RESTART_OVERHEAD_H
    left = (i.deadline - i.now).total_seconds() / 3600
    slack = left - need

    if i.total_attempts >= MAX_ATTEMPTS:
        return Decision("fail", slack < 0, remaining, slack,
                        f"Gave up after {i.total_attempts} attempts. The run kept being interrupted.")
    if i.spot_relaunches < MAX_SPOT_RETRIES and left >= need * DEADLINE_BUFFER:
        return Decision("relaunch_spot", False, remaining, slack,
                        "There is enough time to absorb another interruption, so the job resumes on Spot.")
    if i.spot_relaunches >= MAX_SPOT_RETRIES:
        why = f"Spot was interrupted {i.spot_relaunches + 1} times, so the job moves to on-demand."
    else:
        why = "The deadline leaves no room for another interruption, so the job moves to on-demand."
    return Decision("launch_on_demand", slack < 0, remaining, slack, why)
