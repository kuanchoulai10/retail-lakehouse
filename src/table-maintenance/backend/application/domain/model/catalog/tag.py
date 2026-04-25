"""Define the Tag value object."""

from __future__ import annotations

from dataclasses import dataclass

from core.base.value_object import ValueObject


@dataclass(frozen=True)
class Tag(ValueObject):
    """An immutable tag ref pointing to a snapshot."""

    name: str
    snapshot_id: int
    max_ref_age_ms: int | None = None
