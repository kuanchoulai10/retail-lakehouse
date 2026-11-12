"""Define the ComputeSize enumeration."""

from __future__ import annotations

from enum import StrEnum


class ComputeSize(StrEnum):
    """Enumerate the compute sizes a maintenance attempt can run at, smallest first."""

    S = "S"
    M = "M"
    L = "L"

    def larger(self) -> ComputeSize | None:
        """Return the next larger size, or None at the largest."""
        sizes = list(ComputeSize)
        index = sizes.index(self)
        return sizes[index + 1] if index + 1 < len(sizes) else None

    def smaller(self) -> ComputeSize | None:
        """Return the next smaller size, or None at the smallest."""
        sizes = list(ComputeSize)
        index = sizes.index(self)
        return sizes[index - 1] if index > 0 else None
