"""Define summary_int."""

from __future__ import annotations


def summary_int(summary: dict[str, str], key: str) -> int | None:
    """Return a snapshot summary counter as an int, or None if absent or invalid."""
    try:
        return int(summary[key])
    except KeyError, ValueError:
        return None
