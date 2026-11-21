"""Define the UpdateTableDiscoveryPolicyUseCaseInput."""

from __future__ import annotations

from typing import Any

from base import UseCaseInput


class UpdateTableDiscoveryPolicyUseCaseInput(UseCaseInput):
    """Carry the request to replace a discovery policy's content as a new version."""

    name: str
    content: dict[str, Any]
    version: int
