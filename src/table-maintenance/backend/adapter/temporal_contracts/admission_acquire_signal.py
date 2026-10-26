"""Define the AdmissionAcquireSignal workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdmissionAcquireSignal:
    """Payload of the acquire signal sent to the admission workflow."""

    request_id: str
    requester_workflow_id: str
