"""Define the ManifestProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class ManifestProperties(ValueObject):
    """Manifest file management properties."""

    target_size_bytes: int | None = None
    min_merge_count: int | None = None
    merge_enabled: bool | None = None
