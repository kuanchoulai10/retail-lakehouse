"""Backward-compatible re-export. Canonical location: jobs.domain.exceptions"""

from jobs.domain.exceptions import JobNotFoundError

__all__ = ["JobNotFoundError"]
