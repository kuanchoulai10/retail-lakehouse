"""Define the GetTableDiscoveryPolicyVersionUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetTableDiscoveryPolicyVersionUseCaseInput(UseCaseInput):
    """Carry the request to get one version of a discovery policy."""

    name: str
    version: int
