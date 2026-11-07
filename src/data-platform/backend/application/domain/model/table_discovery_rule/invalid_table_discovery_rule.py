"""Define the InvalidTableDiscoveryRule exception."""

from __future__ import annotations


class InvalidTableDiscoveryRule(ValueError):
    """Raise when a discovery rule violates an invariant."""
