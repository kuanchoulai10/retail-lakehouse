"""Define the ManifestStats value object."""

from __future__ import annotations

from dataclasses import dataclass

from base import ValueObject


@dataclass(frozen=True)
class ManifestStats(ValueObject):
    """Hold the size of one manifest file."""

    length_bytes: int
