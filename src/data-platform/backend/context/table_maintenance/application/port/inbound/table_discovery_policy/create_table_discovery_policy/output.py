"""Define the CreateTableDiscoveryPolicyUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class CreateTableDiscoveryPolicyUseCaseOutput(UseCaseOutput):
    """Describe the result: the new policy's ``dp-`` id, its name and its first version."""

    id: str
    name: str
    description: str
    rules: tuple[dict[str, str], ...]
    version: int
    created_at: datetime
    updated_at: datetime
