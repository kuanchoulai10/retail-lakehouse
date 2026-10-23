"""Define the InvalidDiscoveryRule exception."""

from __future__ import annotations


class InvalidDiscoveryRule(ValueError):
    """Raise when a discovery rule violates an invariant."""
