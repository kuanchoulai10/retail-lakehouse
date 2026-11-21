"""Define the DeleteTableDiscoveryPolicyUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class DeleteTableDiscoveryPolicyUseCaseInput(UseCaseInput):
    """Carry the request to delete a discovery policy and its versions."""

    name: str
