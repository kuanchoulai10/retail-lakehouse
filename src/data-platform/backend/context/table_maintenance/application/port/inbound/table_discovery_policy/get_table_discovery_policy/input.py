"""Define the GetTableDiscoveryPolicyUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetTableDiscoveryPolicyUseCaseInput(UseCaseInput):
    """Carry the request to get the current version of a discovery policy."""

    name: str
