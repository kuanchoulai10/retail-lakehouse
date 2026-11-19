"""Define the GetTableMaintenancePolicyVersionUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class GetTableMaintenancePolicyVersionUseCaseOutput(UseCaseOutput):
    """Describe the result: the policy's ``mp-`` id and current name, and one stored version."""

    id: str
    name: str
    version: int
    content: dict[str, Any]
    created_at: datetime
