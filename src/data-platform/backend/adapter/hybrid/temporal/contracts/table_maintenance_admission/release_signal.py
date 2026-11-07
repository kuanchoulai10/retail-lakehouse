"""Define the AdmissionReleaseSignal workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdmissionReleaseSignal:
    """Payload of the release signal sent to the admission workflow."""

    request_id: str
