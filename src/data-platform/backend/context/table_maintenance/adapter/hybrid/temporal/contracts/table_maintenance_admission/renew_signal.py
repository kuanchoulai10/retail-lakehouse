"""Define the AdmissionRenewSignal workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdmissionRenewSignal:
    """Payload of the renew signal sent to the admission workflow."""

    request_id: str
