"""Define the GetCatalogUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class GetCatalogUseCaseOutput(UseCaseOutput):
    """Describe the catalog."""

    name: str
    type: str
    default_base_location: str | None
    properties: dict[str, str]
    storage_config: dict[str, Any]
    connection_config: dict[str, Any] | None
    entity_version: int
    created_at: datetime | None
    updated_at: datetime | None
