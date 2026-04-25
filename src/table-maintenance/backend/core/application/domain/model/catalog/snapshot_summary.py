"""Define the SnapshotSummary value object."""

from __future__ import annotations

from dataclasses import dataclass

from core.base.value_object import ValueObject


@dataclass(frozen=True)
class SnapshotSummary(ValueObject):
    """Iceberg snapshot summary metadata as raw key-value pairs."""

    data: dict[str, str]
