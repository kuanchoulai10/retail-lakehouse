"""Define the StaleDiscoveryPolicyVersion exception."""

from __future__ import annotations


class StaleDiscoveryPolicyVersion(ValueError):
    """Raise when a discovery policy is replaced from a version that is no longer the current one."""
