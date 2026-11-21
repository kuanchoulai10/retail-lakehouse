"""Define the nearest_attached domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from context.table_maintenance.application.domain.model.shared import PolicyTarget


def nearest_attached[T](candidates: Sequence[PolicyTarget], attached: Mapping[str, T]) -> tuple[PolicyTarget, T] | None:
    """Return the first of ``candidates`` that has an attachment, with what is attached there.

    ``candidates`` run nearest first (``candidate_policy_targets`` or ``enclosing_policy_targets``) and
    ``attached`` is keyed by ``PolicyTarget.key()``. The nearest attachment replaces every one above it
    whole, so the walk stops at the first; None when no candidate has one.
    """
    for candidate in candidates:
        key = candidate.key()
        if key in attached:
            return candidate, attached[key]
    return None
