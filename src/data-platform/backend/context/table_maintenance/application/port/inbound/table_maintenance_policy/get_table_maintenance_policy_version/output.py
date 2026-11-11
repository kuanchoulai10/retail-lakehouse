"""Define the GetTableMaintenancePolicyVersionUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


@dataclass(frozen=True)
class GetTableMaintenancePolicyVersionUseCaseOutput:
    """Describe the result."""

    name: str
    version: int
    content: dict[str, Any]
    created_at: datetime
