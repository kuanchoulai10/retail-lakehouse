"""Define the ValidationError exception."""

from __future__ import annotations


class ValidationError(Exception):
    """Signal that a request carries invalid data."""
