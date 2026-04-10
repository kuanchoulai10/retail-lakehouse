"""Backward-compatible re-export. Canonical location: jobs.domain.job_status

Note: status_from_k8s will move to jobs.adapter.outbound.k8s.status_mapper in a future task.
"""

from jobs.domain.job_status import JobStatus

_STATE_MAP: dict[str, JobStatus] = {
    "RUNNING": JobStatus.RUNNING,
    "COMPLETED": JobStatus.COMPLETED,
    "FAILED": JobStatus.FAILED,
    "SUBMISSION_FAILED": JobStatus.FAILED,
    "INVALIDATING": JobStatus.FAILED,
}


def status_from_k8s(kind: str, state: str) -> JobStatus:
    if kind == "ScheduledSparkApplication":
        return JobStatus.RUNNING
    if not state:
        return JobStatus.PENDING
    return _STATE_MAP.get(state, JobStatus.UNKNOWN)


__all__ = ["JobStatus", "status_from_k8s"]
