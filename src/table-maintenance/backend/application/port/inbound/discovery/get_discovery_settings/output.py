"""Define the GetDiscoverySettingsUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class GetDiscoverySettingsUseCaseOutput:
    """Carry the result."""

    enabled: bool
    updated_at: datetime
