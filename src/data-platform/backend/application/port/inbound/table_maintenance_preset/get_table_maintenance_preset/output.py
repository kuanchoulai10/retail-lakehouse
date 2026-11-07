"""Define the GetTableMaintenancePresetUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


@dataclass(frozen=True)
class GetTableMaintenancePresetUseCaseOutput:
    """Describe the table maintenance preset."""

    id: str
    name: str
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime
