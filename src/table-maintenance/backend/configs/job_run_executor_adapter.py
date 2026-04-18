from __future__ import annotations

from enum import StrEnum


class JobRunExecutorAdapter(StrEnum):
    IN_MEMORY = "in_memory"
    K8S = "k8s"
