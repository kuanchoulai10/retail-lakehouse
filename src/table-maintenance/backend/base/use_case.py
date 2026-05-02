"""Define the UseCase abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from base._inheritance_guard import enforce_max_depth


class UseCase[TInput, TOutput](ABC):
    """A single application-level operation.

    Encapsulates one business action (create a job, expire snapshots, etc.)
    with its dependencies, keeping route handlers thin and the domain logic
    independently testable and reusable across entry points (HTTP, CLI,
    scheduler).

    Type parameters:
        TInput:  the data the caller provides (a request, an id, None).
        TOutput: what the caller gets back (a response, a list, None).

    When TOutput is None the use case acts as a command (side-effect only).
    When TOutput carries data it acts as a query or a command that returns
    a result — no forced CQRS split.

    Usage::

        class CreateJob(UseCase[JobRequest, JobResponse]):
            def __init__(self, repo: JobsRepo) -> None:
                self.repo = repo

            def execute(self, input: JobRequest) -> JobResponse:
                return self.repo.create(input)
    """

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Enforce port + service inheritance depth (max 2)."""
        super().__init_subclass__(**kwargs)
        enforce_max_depth(cls, UseCase, 2)

    @abstractmethod
    def execute(self, request: TInput) -> TOutput:
        """Execute the use case with the given request and return a result."""
