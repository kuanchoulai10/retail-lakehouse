"""Define the InvalidReconciliation exception."""

from __future__ import annotations


class InvalidReconciliation(ValueError):
    """Raise when a reconciliation record breaks its invariants."""
