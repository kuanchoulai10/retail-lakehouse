"""Define the AttachTableMaintenancePolicyUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class AttachTableMaintenancePolicyUseCaseOutput(UseCaseOutput):
    """Carry the place the policy is now attached to, and the attached policy's ``mp-`` id and name.

    ``table_uuid`` is the table's Iceberg uuid for a table, None for a catalog or a namespace.
    """

    target_type: str
    path: tuple[str, ...]
    table_uuid: str | None
    policy_id: str
    policy_name: str
