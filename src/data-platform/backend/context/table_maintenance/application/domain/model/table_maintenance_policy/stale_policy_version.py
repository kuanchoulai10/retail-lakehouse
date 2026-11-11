"""Define the StalePolicyVersion exception."""

from __future__ import annotations


class StalePolicyVersion(ValueError):
    """Raise when a policy is replaced from a version that is no longer the current one."""
