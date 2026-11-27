"""Define the ResolveApplicableTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ResolveApplicableTableMaintenancePolicyUseCaseInput(UseCaseInput):
    """Carry the request to resolve the maintenance policy that applies to a catalog, namespace or table.

    A ``table_uuid`` without ``catalog`` names a table known to table maintenance; its name is read
    from there.
    """

    catalog: str | None = None
    table_uuid: str | None = None
    namespace: str | None = None
    table: str | None = None
