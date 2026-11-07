"""Define the InvalidTableTransition exception."""

from __future__ import annotations


class InvalidTableTransition(ValueError):
    """Raise when a table command is not allowed in its current state."""
