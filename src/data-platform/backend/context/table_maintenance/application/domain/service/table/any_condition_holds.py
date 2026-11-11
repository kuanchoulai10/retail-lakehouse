"""Define the any_condition_holds domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.table_maintenance.application.domain.model.shared import Measurement


def any_condition_holds(measurements: Sequence[Measurement]) -> bool:
    """Return whether any condition among the measurements holds; context measurements are not conditions."""
    return any(m.met is True for m in measurements)
