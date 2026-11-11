"""Define the PartialProgress value object."""

from __future__ import annotations

from pydantic import PositiveInt

from base import ValueObject


class PartialProgress(ValueObject):
    """Configure committing a compaction in several commits."""

    enabled: bool
    max_commits: PositiveInt | None = None
