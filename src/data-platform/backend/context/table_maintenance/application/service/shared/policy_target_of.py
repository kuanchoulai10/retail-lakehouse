"""Define the policy_target_of function."""

from __future__ import annotations

from typing import Any

from context.table_maintenance.application.domain.model.shared import PolicyTarget
from context.table_maintenance.application.exceptions import ValidationError


def policy_target_of(raw: dict[str, Any] | None) -> PolicyTarget | None:
    """Return the target a port's target fields name, None for the platform default.

    Fields that make no target raise ``ValidationError`` naming them.
    """
    if raw is None:
        return None
    try:
        return PolicyTarget.from_primitives(raw)
    except ValueError as exc:
        raise ValidationError(f"invalid policy target {raw!r}: {exc}") from exc
