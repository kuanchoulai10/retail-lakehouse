"""Define the GetTableDiscoveryPolicyVersionUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class GetTableDiscoveryPolicyVersionUseCaseOutput(UseCaseOutput):
    """Describe the result: the policy's ``dp-`` id and current name, and one stored version."""

    id: str
    name: str
    version: int
    description: str
    rules: tuple[dict[str, str], ...]
    created_at: datetime
