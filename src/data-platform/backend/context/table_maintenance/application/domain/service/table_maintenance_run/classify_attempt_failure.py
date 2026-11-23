"""Define the classify_attempt_failure domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_run import (
    AttemptEnding,
    FailureClass,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table_maintenance_run import (
        ContainerExit,
        FailureEvidence,
    )

OOM_TEXTS = ("java.lang.OutOfMemoryError", "OOMKilled", "exit code 52")
PERMANENT_TEXTS = ("NoSuchTableException", "ForbiddenException", "NotAuthorizedException")
COMMIT_CONFLICT_TEXTS = ("CommitFailedException",)
OOM_KILLED_REASON = "OOMKilled"
KILLED_EXIT_CODE = 137
WORKER_OUT_OF_MEMORY_EXIT_CODE = 52
WORKER_ROLE = "worker"
ENDINGS_WITH_TRUSTED_EXITS = frozenset({AttemptEnding.RESULT, AttemptEnding.JOB_FAILED})
PLATFORM_ENDINGS = {
    AttemptEnding.TIMED_OUT: FailureClass.TIMEOUT,
    AttemptEnding.QUEUE_TIMED_OUT: FailureClass.QUEUE_TIMEOUT,
    AttemptEnding.CANCELLED: FailureClass.CANCELLED,
}


def classify_attempt_failure(evidence: FailureEvidence) -> FailureClass:
    """Return why a maintenance attempt failed, from the first rule its evidence meets.

    An attempt the platform itself ended (a timeout, a queue timeout, a cancel) is classified by that
    ending alone. The platform's own kill (a timeout, a cancel, a vanished job) deletes the job's processes, which then
    exit with 137 as an OOM kill would; container exits therefore count only when Spark itself
    reported the failure.
    """
    if evidence.ended_by in PLATFORM_ENDINGS:
        return PLATFORM_ENDINGS[evidence.ended_by]
    texts = (*evidence.texts, *(c.message for c in evidence.containers if c.message))
    trusted_exits = evidence.ended_by in ENDINGS_WITH_TRUSTED_EXITS
    if (trusted_exits and any(_is_oom_exit(c) for c in evidence.containers)) or _any_holds(texts, OOM_TEXTS):
        return FailureClass.OOM
    if _any_holds(texts, PERMANENT_TEXTS):
        return FailureClass.PERMANENT
    if _any_holds(texts, COMMIT_CONFLICT_TEXTS):
        return FailureClass.COMMIT_CONFLICT
    return FailureClass.OTHER


def _is_oom_exit(container: ContainerExit) -> bool:
    if container.reason == OOM_KILLED_REASON or container.exit_code == KILLED_EXIT_CODE:
        return True
    return container.role == WORKER_ROLE and container.exit_code == WORKER_OUT_OF_MEMORY_EXIT_CODE


def _any_holds(texts: tuple[str, ...], patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for text in texts for pattern in patterns)
