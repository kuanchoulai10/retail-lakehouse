"""Define the TablePropertyNotResettable exception."""

from __future__ import annotations


class TablePropertyNotResettable(ValueError):
    """Raise when a reset to default names a property that must not be reset."""
