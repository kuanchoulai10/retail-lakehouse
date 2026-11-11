"""Define the StaleDiscoveryRulesVersion exception."""

from __future__ import annotations


class StaleDiscoveryRulesVersion(ValueError):
    """Raise when the discovery rules are replaced from a version that is no longer the current one."""
