"""Define the UnknownDiscoveryRuleId exception."""

from __future__ import annotations


class UnknownDiscoveryRuleId(ValueError):
    """Raise when content names a rule id the policy's current version does not hold and the request did not issue."""
