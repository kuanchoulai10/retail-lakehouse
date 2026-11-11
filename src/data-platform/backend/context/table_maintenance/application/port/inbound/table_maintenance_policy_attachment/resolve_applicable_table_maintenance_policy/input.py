"""Define the ResolveApplicableTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResolveApplicableTableMaintenancePolicyUseCaseInput:
    """Carry the request to resolve the maintenance policy that applies to a catalog, namespace or table."""

    catalog: str
    table_uuid: str | None = None
    namespace: str | None = None
    table: str | None = None
