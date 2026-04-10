"""Backward-compatible re-export.

Canonical locations: jobs.domain.job_status, jobs.adapter.outbound.k8s.status_mapper
"""

from jobs.adapter.outbound.k8s.status_mapper import status_from_k8s
from jobs.domain.job_status import JobStatus

__all__ = ["JobStatus", "status_from_k8s"]
