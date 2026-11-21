"""Define the policy_target_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared import PolicyTarget


def policy_target_fields(target: PolicyTarget) -> dict[str, object]:
    """Return a target as an output field: ``type`` and ``path``, and ``table_uuid`` for a table."""
    fields: dict[str, object] = {"type": target.type.value, "path": list(target.path)}
    if target.table_uuid is not None:
        fields["table_uuid"] = target.table_uuid
    return fields
