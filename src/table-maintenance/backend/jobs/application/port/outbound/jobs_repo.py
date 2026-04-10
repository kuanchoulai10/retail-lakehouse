from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jobs.adapter.inbound.web.dto import JobRequest
    from jobs.domain.job import Job


class BaseJobsRepo(ABC):
    @abstractmethod
    def create(self, request: JobRequest) -> Job: ...

    @abstractmethod
    def list_all(self) -> list[Job]: ...

    @abstractmethod
    def get(self, name: str) -> Job: ...

    @abstractmethod
    def delete(self, name: str) -> None: ...
