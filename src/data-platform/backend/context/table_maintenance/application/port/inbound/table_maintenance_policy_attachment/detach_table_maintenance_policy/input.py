"""Define the DetachTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class DetachTableMaintenancePolicyUseCaseInput(UseCaseInput):
    """Carry the request to detach the maintenance policy from a catalog, namespace or table.

    ``policy_name``, when given, must be the policy attached there. ``table_uuid`` names a table
    target that is no longer in the catalog.
    """

    target_type: str
    path: tuple[str, ...]
    table_uuid: str | None = None
    policy_name: str | None = None
