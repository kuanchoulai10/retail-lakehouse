"""Define the NotFoundError exception."""

from __future__ import annotations


class NotFoundError(Exception):
    """Signal that a referenced record does not exist."""
