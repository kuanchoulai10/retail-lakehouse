"""Define the ManifestStats value object."""

from __future__ import annotations

from base import ValueObject


class ManifestStats(ValueObject):
    """Hold the size of one manifest file."""

    length_bytes: int
