"""Define the UpdateTableSettingsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UpdateTableSettingsUseCaseInput:
    """Carry the request to replace a table's settings."""

    uuid: str
    settings: dict[str, Any]
