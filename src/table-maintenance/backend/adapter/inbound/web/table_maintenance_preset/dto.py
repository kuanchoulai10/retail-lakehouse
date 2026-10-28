"""Define the table maintenance preset API DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateTableMaintenancePresetApiRequest(BaseModel):
    """Carry the body that creates a table maintenance preset."""

    model_config = ConfigDict(extra="forbid")

    name: str
    settings: dict[str, Any] = Field(default_factory=dict)


class UpdateTableMaintenancePresetApiRequest(BaseModel):
    """Carry the body that changes a table maintenance preset; omitted fields stay."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    settings: dict[str, Any] | None = None


class TableMaintenancePresetApiResponse(BaseModel):
    """Describe a table maintenance preset."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime
