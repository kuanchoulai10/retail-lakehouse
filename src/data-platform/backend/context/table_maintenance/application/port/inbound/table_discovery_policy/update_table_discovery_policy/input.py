"""Define the UpdateTableDiscoveryPolicyUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class UpdateTableDiscoveryPolicyUseCaseInput(UseCaseInput):
    """Carry the request to revise a discovery policy's description and rules as a new version."""

    name: str
    description: str
    rules: tuple[dict[str, str], ...]
    version: int
