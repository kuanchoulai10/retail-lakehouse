"""Define the JobRunExecutorAdapter enumeration."""

from __future__ import annotations

from enum import StrEnum


class JobRunExecutorAdapter(StrEnum):
    """Enumerate supported JobRunExecutor implementations."""

    IN_MEMORY = "in_memory"
    K8S = "k8s"
