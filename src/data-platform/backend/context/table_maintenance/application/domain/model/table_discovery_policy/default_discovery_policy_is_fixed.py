"""Define the DefaultDiscoveryPolicyIsFixed exception."""

from __future__ import annotations


class DefaultDiscoveryPolicyIsFixed(ValueError):
    """Raise when the platform's default discovery policy is to be changed or deleted; it never is."""
