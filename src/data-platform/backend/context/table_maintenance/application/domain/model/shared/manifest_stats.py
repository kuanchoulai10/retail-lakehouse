"""Define the ManifestStats value object."""

from __future__ import annotations

from pydantic import NonNegativeInt

from base import ValueObject


class ManifestStats(ValueObject):
    """Hold the size of one manifest file and how many entries it has per status."""

    length_bytes: int
    added_entries: NonNegativeInt = 0
    existing_entries: NonNegativeInt = 0
    deleted_entries: NonNegativeInt = 0
