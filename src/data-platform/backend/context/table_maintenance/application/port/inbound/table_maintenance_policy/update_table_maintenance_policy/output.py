"""Define the UpdateTableMaintenancePolicyUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class UpdateTableMaintenancePolicyUseCaseOutput(UseCaseOutput):
    """Describe the result: the policy's ``mp-`` id, its name and its new version."""

    id: str
    name: str
    is_default: bool
    content: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime
