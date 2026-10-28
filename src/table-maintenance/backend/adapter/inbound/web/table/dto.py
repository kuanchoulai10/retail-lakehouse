"""Define the table API DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, RootModel


class TableApiResponse(BaseModel):
    """Describe a table."""

    model_config = ConfigDict(from_attributes=True)

    uuid: str
    catalog: str
    namespace: str
    table: str
    status: str
    selection: str
    settings: dict[str, Any] | None
    matched_rule_id: str | None
    source_preset_id: str | None
    operation_states: dict[str, dict[str, Any]]
    registered_at: datetime
    updated_at: datetime


class UpdateTableSettingsApiRequest(RootModel[dict[str, Any]]):
    """Carry the settings object that replaces the table settings."""


class IncludeTableApiRequest(BaseModel):
    """Carry the body that includes a table by hand."""

    model_config = ConfigDict(extra="forbid")

    catalog: str
    namespace: str
    table: str
    preset_id: str


class ExcludeTableApiRequest(BaseModel):
    """Carry the body that excludes a table by hand."""

    model_config = ConfigDict(extra="forbid")

    catalog: str
    namespace: str
    table: str


class TriggerTableMaintenanceApiRequest(BaseModel):
    """Carry the operations to run now."""

    model_config = ConfigDict(extra="forbid")

    operations: list[str]


class TriggerTableMaintenanceApiResponse(BaseModel):
    """Tell whether the trigger was accepted."""

    model_config = ConfigDict(from_attributes=True)

    accepted: bool
