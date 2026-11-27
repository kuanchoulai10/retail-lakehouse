"""Define the AttachTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class AttachTableMaintenancePolicyUseCaseInput(UseCaseInput):
    """Carry the request to attach the policy ``policy_name`` to the catalog, namespace or table at ``path``.

    ``path`` is the catalog name, then the namespace levels, then the table name for a table.
    """

    policy_name: str
    target_type: str
    path: tuple[str, ...]
