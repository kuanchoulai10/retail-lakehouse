"""Define the GetTableMaintenancePolicyVersionUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class GetTableMaintenancePolicyVersionUseCaseOutput(UseCaseOutput):
    """Describe the result."""

    name: str
    version: int
    content: dict[str, Any]
    created_at: datetime
