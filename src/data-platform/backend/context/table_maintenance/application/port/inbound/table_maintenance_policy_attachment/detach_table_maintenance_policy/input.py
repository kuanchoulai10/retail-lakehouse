"""Define the DetachTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetachTableMaintenancePolicyUseCaseInput:
    """Carry the request to detach the maintenance policy from a catalog, namespace or table."""

    target_type: str
    path: tuple[str, ...]
    table_uuid: str | None = None
