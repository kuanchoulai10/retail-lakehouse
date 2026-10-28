"""Define the discovery rule API DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreateTableDiscoveryRuleApiRequest(BaseModel):
    """Carry the body that creates a discovery rule."""

    model_config = ConfigDict(extra="forbid")

    priority: int
    effect: str
    catalog_pattern: str = "*"
    namespace_pattern: str = "*"
    table_pattern: str = "*"
    preset_id: str | None = None
    enabled: bool = True


class UpdateTableDiscoveryRuleApiRequest(CreateTableDiscoveryRuleApiRequest):
    """Carry the body that replaces the fields of a discovery rule."""


class TableDiscoveryRuleApiResponse(BaseModel):
    """Describe a discovery rule."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    priority: int
    effect: str
    catalog_pattern: str
    namespace_pattern: str
    table_pattern: str
    preset_id: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime
