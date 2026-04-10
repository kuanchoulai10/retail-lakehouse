from __future__ import annotations

from base.use_case import UseCase

from jobs.domain.job import Job


class GetJobUseCase(UseCase[str, Job]):
    """Retrieve a single job by its ID."""
