from __future__ import annotations

from abc import ABC, abstractmethod


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

    @abstractmethod
    def execute(self, request: TInput) -> TOutput: ...
