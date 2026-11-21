"""Define the CreateTableDiscoveryPolicyUseCaseInput."""

from __future__ import annotations

from typing import Any

from base import UseCaseInput


class CreateTableDiscoveryPolicyUseCaseInput(UseCaseInput):
    """Carry the request to create a discovery policy at version 1."""

    name: str
    content: dict[str, Any]
