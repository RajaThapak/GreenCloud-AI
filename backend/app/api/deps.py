from collections.abc import Iterator

from sqlalchemy.orm import Session

from ..config import settings
from ..db import SessionLocal
from ..execution.fake import FakeCloud
from ..execution.manager import RunManager, utcnow
from ..execution.placement import OptimizerPlacements
from .errors import ApiError


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_cloud: FakeCloud | None = None


def get_cloud() -> FakeCloud:
    global _cloud
    if settings.cloud_provider != "fake":
        raise ApiError(501, "The AWS provider arrives in a later chunk.", "provider_unavailable")
    if _cloud is None:
        _cloud = FakeCloud(utcnow())
    return _cloud


def make_manager(db: Session, cloud: FakeCloud) -> RunManager:
    return RunManager(db, cloud, OptimizerPlacements(db), clock=lambda: cloud.now)
