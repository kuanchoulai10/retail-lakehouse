"""Define the ConflictError exception."""

from __future__ import annotations


class ConflictError(Exception):
    """Signal that a write conflicts with the current state of a catalog object."""
