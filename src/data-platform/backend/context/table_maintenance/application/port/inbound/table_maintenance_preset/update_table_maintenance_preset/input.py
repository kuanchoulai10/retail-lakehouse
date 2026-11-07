"""Define the UpdateTableMaintenancePresetUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UpdateTableMaintenancePresetUseCaseInput:
    """Carry the request to rename a table maintenance preset or replace its settings."""

    id: str
    name: str | None = None
    settings: dict[str, Any] | None = None
