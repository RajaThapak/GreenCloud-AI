"""Try the optimizer on your real data:  python -m app.scheduler.demo --mode Carbon --duration 6"""
import argparse
from datetime import datetime, timedelta, timezone

from ..db import SessionLocal
from .models import SchedulerError, WorkloadSpec
from .service import plan_workload


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", default="Balanced", choices=["Cost", "Balanced", "Carbon"])
    p.add_argument("--duration", type=float, default=6)
    p.add_argument("--deadline-hours", type=float, default=30)
    p.add_argument("--vcpu", type=int, default=4)
    p.add_argument("--memory", type=float, default=16)
    p.add_argument("--gpus", type=int, default=1)
    p.add_argument("--save", action="store_true")
    a = p.parse_args()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    spec = WorkloadSpec("demo", a.duration, now + timedelta(hours=a.deadline_hours), a.mode, a.vcpu, a.memory, a.gpus)
    try:
        with SessionLocal.begin() as s:
            r = plan_workload(s, spec, now, save=a.save)
    except SchedulerError as e:
        print("No plan:", e)
        return
    for label, c in [("BEST", r.best)] + [("ALT ", x) for x in r.alternatives]:
        print(f"{label} {c.region:13} {c.instance:11} {c.purchase:9} start {c.start:%a %H:%M} "
              f"cost ${c.cost:.2f} carbon {c.carbon_kg:.1f} kg risk {c.risk_label}")
    print("\nWhy:"); [print(" -", x) for x in r.reasons]
    if r.warnings:
        print("\nWarnings:"); [print(" -", x) for x in r.warnings]


if __name__ == "__main__":
    main()
