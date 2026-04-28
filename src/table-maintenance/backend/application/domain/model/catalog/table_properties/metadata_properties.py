"""Define the MetadataProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class MetadataProperties(ValueObject):
    """Table metadata management properties."""

    compression_codec: str | None = None
    delete_after_commit_enabled: bool | None = None
    previous_versions_max: int | None = None
