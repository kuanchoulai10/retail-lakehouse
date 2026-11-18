"""Define the TriggerTableMaintenanceUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class TriggerTableMaintenanceUseCaseInput(UseCaseInput):
    """Carry the request to trigger maintenance operations on a table now."""

    uuid: str
    operations: tuple[str, ...]
