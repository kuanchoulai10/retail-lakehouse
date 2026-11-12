"""Define the AdmissionAcquireSignal workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdmissionAcquireSignal:
    """Payload of the acquire signal sent to the admission workflow.

    ``lease_seconds`` is how long the slot may be held without a renew: the
    requester's attempt deadline plus ``ADMISSION_LEASE_MARGIN_SECONDS``. A request
    without one (sent before requests carried it) gets the workflow's lease.
    """

    request_id: str
    requester_workflow_id: str
    lease_seconds: int | None = None
