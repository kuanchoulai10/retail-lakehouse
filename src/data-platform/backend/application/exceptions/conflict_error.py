"""Define the ConflictError exception."""

from __future__ import annotations


class ConflictError(Exception):
    """Signal that a write conflicts with an existing record."""
