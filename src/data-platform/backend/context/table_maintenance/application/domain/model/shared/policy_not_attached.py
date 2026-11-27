"""Define the PolicyNotAttached exception."""

from __future__ import annotations


class PolicyNotAttached(ValueError):
    """Raise when a policy is detached from a catalog, namespace or table it is not attached to."""
