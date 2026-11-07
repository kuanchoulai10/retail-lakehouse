"""Define the NullOrder enum."""

from __future__ import annotations

from enum import StrEnum


class NullOrder(StrEnum):
    """Where nulls go in one sort field."""

    NULLS_FIRST = "nulls-first"
    NULLS_LAST = "nulls-last"
