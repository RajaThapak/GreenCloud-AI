"""Runs and monitors jobs: launch, detect interruptions, recover, account for cost."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.execution import ExecutionRun, RunAttempt
from . import config as C
from . import states as S
from .datatypes import CapacityError, InstanceInfo, LaunchRequest
from .provider import CloudProvider
from .recovery import RecoveryInput, decide

log = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RunManager:
    def __init__(self, session: Session, cloud: CloudProvider, placements, clock=utcnow, notify=None):
        self.s, self.cloud, self.placements, self.clock = session, cloud, placements, clock
        self.notify = notify or (lambda run, event, msg: log.info("run %s %s: %s", run.id, event, msg))

    # ---------- queries ----------
    def _attempts(self, run):
        return list(self.s.scalars(select(RunAttempt).where(RunAttempt.run_id == run.id).order_by(RunAttempt.number)))

    def _active(self, run):
        return self.s.scalars(select(RunAttempt).where(RunAttempt.run_id == run.id, RunAttempt.ended_at.is_(None))
                              .order_by(RunAttempt.number.desc())).first()

    # ---------- public API ----------
    def start(self, run_id: int):
        run = self.s.get(ExecutionRun, run_id)
        if run.status != S.SCHEDULED:
            return run
        now = self.clock()
        run.started_at = run.last_heartbeat = now
        if self._launch(run, "Spot", run.duration_h):
            run.status = S.RUNNING
        else:
            run.status, run.launch_failures = S.RECOVERING, run.launch_failures + 1
            self.notify(run, "delayed", "No capacity was available, so the launch will be retried.")
        return run

    def tick(self, run_id: int):
        """One monitoring step. Safe to call repeatedly: it never launches twice for the same event."""
        run = self.s.get(ExecutionRun, run_id)
        if run is None or run.status not in S.ACTIVE:
            return run
        att = self._active(run)
        if att is None:                                   # was waiting for capacity
            self._relaunch(run)
            return run
        now = self.clock()
        info = self.cloud.describe(att.instance_id)
        if run.checkpointing:
            ckpt = self.cloud.latest_checkpoint(run.id)
            if ckpt is not None:
                run.progress = max(run.progress, ckpt)

        if info.state == "running":
            hb = self.cloud.heartbeat(att.instance_id)
            if hb:
                run.last_heartbeat = hb
            if now - run.last_heartbeat > timedelta(minutes=C.HEARTBEAT_TIMEOUT_MIN):
                self.cloud.terminate(att.instance_id)
                self._interrupted(run, att, now, S.END_LOST)
            elif att.notice_at is None and self.cloud.notice(att.instance_id):
                att.notice_at = now
                self.notify(run, "warning", "AWS announced it will reclaim the instance. Saving a final checkpoint.")
        elif info.state == "finished":
            self._finish(run, att, info)
        elif info.state == "failed":
            self._close(run, att, S.END_FAILED, info.ended_at)
            self._fail(run, "The job itself exited with an error, so it was not retried. Check the job logs.")
        else:                                             # interrupted, terminated or missing
            self._interrupted(run, att, info.ended_at or now, S.END_INTERRUPTED)
        return run

    def cancel(self, run_id: int):
        run = self.s.get(ExecutionRun, run_id)
        if run.status in S.TERMINAL:
            return run
        att = self._active(run)
        if att:
            self.cloud.terminate(att.instance_id)
            self._close(run, att, S.END_CANCELLED, None)
        run.status, run.finished_at = S.CANCELLED, self.clock()
        return run

    def reap(self) -> int:
        """Terminate instances that belong to no active run, so you never pay for orphans."""
        now, killed = self.clock(), 0
        for iid, rid, launched in self.cloud.list_running():
            if now - launched < timedelta(minutes=C.REAPER_GRACE_MIN):
                continue
            run = self.s.get(ExecutionRun, rid)
            active = self._active(run) if run else None
            if run is None or run.status in S.TERMINAL or active is None or active.instance_id != iid:
                self.cloud.terminate(iid)
                killed += 1
        return killed

    # ---------- internals ----------
    def _launch(self, run, pref: str, remaining_h: float) -> bool:
        now = self.clock()
        n = len(self._attempts(run)) + 1
        for p in self.placements(run, remaining_h, pref, now):
            req = LaunchRequest(run.id, n, p.region, p.instance, p.purchase, run.progress, run.duration_h,
                                run.checkpointing, run.image, token=f"run{run.id}-attempt{n}")
            try:
                iid = self.cloud.launch(req)
            except CapacityError:
                continue
            self.s.add(RunAttempt(run_id=run.id, number=n, region=p.region, instance_type=p.instance,
                                  purchase=p.purchase, instance_id=iid, started_at=now,
                                  start_progress=run.progress, price_per_h=p.price_per_h, kg_per_h=p.kg_per_h))
            self.s.flush()
            run.last_heartbeat, run.launch_failures = now, 0
            return True
        return False

    def _close(self, run, att, reason: str, ended_at):
        now = self.clock()
        end = min(ended_at or now, now)
        att.ended_at, att.end_reason = end, reason
        att.end_progress = 1.0 if reason == S.END_COMPLETED else run.progress
        hours = max(0.0, (end - att.started_at).total_seconds() / 3600)
        att.cost, att.carbon_kg = att.price_per_h * hours, att.kg_per_h * hours
        att.wasted_h = max(0.0, hours - max(0.0, att.end_progress - att.start_progress) * run.duration_h)
        run.actual_cost += att.cost
        run.actual_carbon_kg += att.carbon_kg
        run.wasted_h += att.wasted_h
        self.s.flush()

    def _finish(self, run, att, info: InstanceInfo):
        self._close(run, att, S.END_COMPLETED, info.ended_at)
        self.cloud.terminate(att.instance_id)
        run.progress, run.finished_at = 1.0, info.ended_at or self.clock()
        run.status = S.RECOVERED if run.interruptions else S.COMPLETED
        self.notify(run, "completed", f"Finished after {run.interruptions} interruption(s). Cost ${run.actual_cost:.2f}.")

    def _fail(self, run, reason: str):
        run.status, run.failure_reason, run.finished_at = S.FAILED, reason, self.clock()
        self.notify(run, "failed", reason)

    def _interrupted(self, run, att, ended_at, reason: str):
        if not run.checkpointing:
            run.progress = 0.0                            # nothing was saved: all work is lost
        self._close(run, att, reason, ended_at)
        run.interruptions += 1
        self.notify(run, "interrupted", f"Attempt {att.number} on {att.instance_type} in {att.region} was lost.")
        self._relaunch(run)

    def _relaunch(self, run):
        d = decide(RecoveryInput(self.clock(), run.deadline, run.duration_h, run.progress,
                                 run.spot_relaunches, len(self._attempts(run))))
        if d.action == "fail":
            return self._fail(run, d.reason)
        if d.at_risk and not run.deadline_at_risk:
            self.notify(run, "at_risk", "This job may miss its deadline. It continues on the fastest option.")
        run.deadline_at_risk = run.deadline_at_risk or d.at_risk
        pref = "Spot" if d.action == "relaunch_spot" else "On-demand"
        if self._launch(run, pref, d.remaining_h):
            if self._active(run).purchase == "Spot":
                run.spot_relaunches += 1
            run.status = S.RUNNING
            self.notify(run, "recovered", d.reason)
        else:
            run.status, run.launch_failures = S.RECOVERING, run.launch_failures + 1
            if run.launch_failures > C.MAX_LAUNCH_FAILURES:
                self._fail(run, "No capacity could be found anywhere. Try again later or allow more regions.")
