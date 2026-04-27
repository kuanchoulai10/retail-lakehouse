"""Define the SubmitJobRunGatewayAdapter enumeration."""

from __future__ import annotations

from enum import StrEnum


class SubmitJobRunGatewayAdapter(StrEnum):
    """Enumerate supported SubmitJobRunGateway implementations."""

    IN_MEMORY = "in_memory"
    K8S = "k8s"
