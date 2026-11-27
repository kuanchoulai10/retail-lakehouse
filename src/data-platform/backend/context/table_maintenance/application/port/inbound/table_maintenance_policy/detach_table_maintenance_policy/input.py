"""Define the DetachTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class DetachTableMaintenancePolicyUseCaseInput(UseCaseInput):
    """Carry the request to detach the policy ``policy_name`` from the catalog, namespace or table at ``path``.

    ``path`` is the catalog name, then the namespace levels, then the table name for a table.
    """

    policy_name: str
    target_type: str
    path: tuple[str, ...]
