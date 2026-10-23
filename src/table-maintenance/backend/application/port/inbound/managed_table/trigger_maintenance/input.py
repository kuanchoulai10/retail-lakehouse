"""Define the TriggerMaintenanceUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerMaintenanceUseCaseInput:
    """Carry the request to trigger maintenance operations on a table now."""

    uuid: str
    operations: list[str]
