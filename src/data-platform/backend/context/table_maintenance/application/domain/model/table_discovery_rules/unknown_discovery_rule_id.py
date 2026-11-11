"""Define the UnknownDiscoveryRuleId exception."""

from __future__ import annotations


class UnknownDiscoveryRuleId(ValueError):
    """Raise when a replacement names a rule id that is neither in the list nor declared new."""
