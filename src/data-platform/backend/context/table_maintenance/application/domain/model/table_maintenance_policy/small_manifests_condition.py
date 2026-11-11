"""Define the SmallManifestsCondition value object."""

from __future__ import annotations

from pydantic import PositiveInt

from base import ValueObject


class SmallManifestsCondition(ValueObject):
    """A threshold on small manifests.

    ``smaller_than_bytes`` of None falls back to the table property
    ``commit.manifest.target-size-bytes``, else 8 MiB.
    """

    at_least: PositiveInt
    smaller_than_bytes: PositiveInt | None = None
