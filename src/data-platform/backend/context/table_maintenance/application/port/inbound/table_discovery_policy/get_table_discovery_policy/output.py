"""Define the GetTableDiscoveryPolicyUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class GetTableDiscoveryPolicyUseCaseOutput(UseCaseOutput):
    """Describe the result: the policy's ``dp-`` id, its name and its current version."""

    id: str
    name: str
    description: str
    rules: tuple[dict[str, str], ...]
    version: int
    created_at: datetime
    updated_at: datetime
