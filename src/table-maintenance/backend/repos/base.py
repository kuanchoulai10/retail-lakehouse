from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.requests import JobRequest
    from models.responses import JobResponse


class JobNotFoundError(Exception):
    """Raised when a job is not found in the repository."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Job {name!r} not found")


class JobsRepo(ABC):
    @abstractmethod
    def create(self, request: JobRequest) -> JobResponse: ...

    @abstractmethod
    def list_all(self) -> list[JobResponse]: ...

    @abstractmethod
    def get(self, name: str) -> JobResponse: ...

    @abstractmethod
    def delete(self, name: str) -> None: ...
