"""Define the GetTableDiscoveryPolicyVersionUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class GetTableDiscoveryPolicyVersionUseCaseOutput(UseCaseOutput):
    """Describe the result: the policy's ``dp-`` id and current name, and one stored version."""

    id: str
    name: str
    is_default: bool
    version: int
    content: dict[str, Any]
    created_at: datetime
