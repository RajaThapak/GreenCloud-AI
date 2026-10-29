"""The cloud as the run manager sees it. FakeCloud (tests) and the AWS provider (chunk 8) both implement it."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from .datatypes import InstanceInfo, LaunchRequest


class CloudProvider(ABC):
    @abstractmethod
    def launch(self, req: LaunchRequest) -> str:
        """Start the job on a new instance and return its id. Raise CapacityError if none is available.
        Must be idempotent per req.token. Tag the instance with run id and attempt number."""

    @abstractmethod
    def describe(self, instance_id: str) -> InstanceInfo: ...

    @abstractmethod
    def terminate(self, instance_id: str) -> None: ...

    @abstractmethod
    def notice(self, instance_id: str) -> bool:
        """True once the two-minute interruption warning has been issued."""

    @abstractmethod
    def heartbeat(self, instance_id: str) -> datetime | None:
        """When the job last reported in, or None."""

    @abstractmethod
    def latest_checkpoint(self, run_id: int) -> float | None:
        """Progress (0..1) of the newest checkpoint, or None if the job has never saved one."""

    @abstractmethod
    def list_running(self) -> list[tuple[str, int, datetime]]:
        """(instance_id, run_id, launched_at) for every instance tagged as ours and still running."""


def get_cloud() -> CloudProvider:
    raise NotImplementedError("The AWS provider is built in chunk 8. Use FakeCloud for now.")
