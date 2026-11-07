"""Define the NotFoundError exception."""

from __future__ import annotations


class NotFoundError(Exception):
    """Signal that the requested catalog object does not exist."""
