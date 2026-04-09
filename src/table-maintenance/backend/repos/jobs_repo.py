from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.job_request import JobRequest
    from models.job_response import JobResponse


class JobsRepo(ABC):
    @abstractmethod
    def create(self, request: JobRequest) -> JobResponse: ...

    @abstractmethod
    def list_all(self) -> list[JobResponse]: ...

    @abstractmethod
    def get(self, name: str) -> JobResponse: ...

    @abstractmethod
    def delete(self, name: str) -> None: ...
