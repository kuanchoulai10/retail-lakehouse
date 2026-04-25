"""Define the RetentionPolicy value object."""

from __future__ import annotations

from dataclasses import dataclass

from core.base.value_object import ValueObject


@dataclass(frozen=True)
class RetentionPolicy(ValueObject):
    """Branch-level retention configuration."""

    max_snapshot_age_ms: int | None = None
    max_ref_age_ms: int | None = None
    min_snapshots_to_keep: int | None = None
