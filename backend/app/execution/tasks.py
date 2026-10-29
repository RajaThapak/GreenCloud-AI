"""Celery tasks. Do NOT add them to beat_schedule until the AWS provider exists (chunk 8)."""
from sqlalchemy import select

from ..celery_app import celery
from ..db import SessionLocal
from ..models.execution import ExecutionRun
from .manager import RunManager
from .placement import OptimizerPlacements
from .provider import get_cloud
from .states import ACTIVE


def _manager(session):
    return RunManager(session, get_cloud(), OptimizerPlacements(session))


@celery.task
def start_run(run_id: int):
    with SessionLocal.begin() as s:
        _manager(s).start(run_id)


@celery.task
def monitor_runs():
    with SessionLocal.begin() as s:
        mgr = _manager(s)
        for rid in list(s.scalars(select(ExecutionRun.id).where(ExecutionRun.status.in_(ACTIVE)))):
            mgr.tick(rid)


@celery.task
def reap_orphans():
    with SessionLocal.begin() as s:
        return _manager(s).reap()
