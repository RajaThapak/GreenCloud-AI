"""A fake cloud with a controllable clock, so interruptions can be injected at exact moments."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from .datatypes import CapacityError, InstanceInfo, LaunchRequest
from .provider import CloudProvider


@dataclass
class _Inst:
    id: str
    req: LaunchRequest
    started_at: datetime
    state: str = "running"
    ended_at: datetime | None = None
    interrupt_at: datetime | None = None
    silent_at: datetime | None = None


class FakeCloud(CloudProvider):
    def __init__(self, start: datetime, checkpoint_interval_h: float = 0.25):
        self.now = start
        self.interval = checkpoint_interval_h
        self.instances: dict[str, _Inst] = {}
        self.launch_log: list[LaunchRequest] = []
        self._tokens: dict[str, str] = {}
        self._blocked: set = set()
        self._ckpt: dict[int, float] = {}
        self._seq = 0

    # ---- controls for tests ----
    def fail_launch(self, region, instance_type, purchase):
        self._blocked.add((region, instance_type, purchase))

    def clear_failures(self):
        self._blocked.clear()

    def interrupt_in(self, instance_id, hours):
        self.instances[instance_id].interrupt_at = self.now + timedelta(hours=hours)

    def make_silent(self, instance_id):
        self.instances[instance_id].silent_at = self.now

    def fail_job(self, instance_id):
        i = self.instances[instance_id]
        i.state, i.ended_at = "failed", self.now

    def advance(self, hours: float):
        """Move time forward, finishing or interrupting jobs and saving checkpoints on the way."""
        target = self.now + timedelta(hours=hours)
        for i in self.instances.values():
            if i.state != "running":
                continue
            r = i.req
            finish = i.started_at + timedelta(hours=(1 - r.start_progress) * r.total_duration_h)
            events = [(finish, "finished")] + ([(i.interrupt_at, "interrupted")] if i.interrupt_at else [])
            when, what = min(events)
            t_eff = target
            if when <= target:
                i.state, i.ended_at, t_eff = what, when, when
            if r.checkpointing:
                steps = math.floor((t_eff - i.started_at).total_seconds() / 3600 / self.interval + 1e-9)
                p = min(1.0, r.start_progress + steps * self.interval / r.total_duration_h)
                self._ckpt[r.run_id] = max(self._ckpt.get(r.run_id, 0.0), p)
        self.now = target

    # ---- CloudProvider ----
    def launch(self, req):
        if req.token in self._tokens:
            return self._tokens[req.token]
        if (req.region, req.instance_type, req.purchase) in self._blocked:
            raise CapacityError(f"No {req.purchase} capacity for {req.instance_type} in {req.region}")
        self._seq += 1
        iid = f"i-{self._seq:04d}"
        self.instances[iid] = _Inst(iid, req, self.now)
        self._tokens[req.token] = iid
        self.launch_log.append(req)
        return iid

    def describe(self, instance_id):
        i = self.instances.get(instance_id)
        return InstanceInfo("missing") if i is None else InstanceInfo(i.state, i.ended_at)

    def terminate(self, instance_id):
        i = self.instances.get(instance_id)
        if i and i.state == "running":
            i.state, i.ended_at = "terminated", self.now

    def notice(self, instance_id):
        i = self.instances.get(instance_id)
        return bool(i and i.state == "running" and i.interrupt_at
                    and self.now >= i.interrupt_at - timedelta(minutes=2))

    def heartbeat(self, instance_id):
        i = self.instances.get(instance_id)
        if not i or i.state != "running":
            return None
        return min(self.now, i.silent_at) if i.silent_at else self.now

    def latest_checkpoint(self, run_id):
        return self._ckpt.get(run_id)

    def list_running(self):
        return [(i.id, i.req.run_id, i.started_at) for i in self.instances.values() if i.state == "running"]
