"""Provide the status_from_k8s mapping function."""

from application.domain.model.job_run import JobRunStatus

_STATE_MAP: dict[str, JobRunStatus] = {
    "RUNNING": JobRunStatus.RUNNING,
    "COMPLETED": JobRunStatus.COMPLETED,
    "FAILED": JobRunStatus.FAILED,
    "SUBMISSION_FAILED": JobRunStatus.FAILED,
    "INVALIDATING": JobRunStatus.FAILED,
}


def status_from_k8s(kind: str, state: str) -> JobRunStatus:
    """Map a Kubernetes SparkApplication state to a JobRunStatus."""
    if kind == "ScheduledSparkApplication":
        return JobRunStatus.RUNNING
    if not state:
        return JobRunStatus.PENDING
    return _STATE_MAP.get(state, JobRunStatus.FAILED)
