"""Define the AttachTableDiscoveryPolicyUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class AttachTableDiscoveryPolicyUseCaseInput(UseCaseInput):
    """Carry the request to attach a discovery policy to a catalog, namespace or table."""

    policy_name: str
    target_type: str
    path: tuple[str, ...]
