"""Define the CreateTableDiscoveryPolicyUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class CreateTableDiscoveryPolicyUseCaseInput(UseCaseInput):
    """Carry the request to create a discovery policy at version 1."""

    name: str
    description: str
    rules: tuple[dict[str, str], ...]
