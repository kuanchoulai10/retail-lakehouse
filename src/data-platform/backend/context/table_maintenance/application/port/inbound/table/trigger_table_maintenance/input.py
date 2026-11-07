"""Define the TriggerTableMaintenanceUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerTableMaintenanceUseCaseInput:
    """Carry the request to trigger maintenance operations on a table now."""

    uuid: str
    operations: list[str]
