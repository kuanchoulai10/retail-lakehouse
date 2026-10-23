"""Define the InvalidRunTransition exception."""

from __future__ import annotations


class InvalidRunTransition(ValueError):
    """Raise when a maintenance run command is not allowed in its current state."""
