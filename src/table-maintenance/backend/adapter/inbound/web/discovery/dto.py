"""Define the discovery API DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UpdateDiscoverySettingsApiRequest(BaseModel):
    """Carry the body that switches discovery on or off."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool


class DiscoverySettingsApiResponse(BaseModel):
    """Describe the discovery settings."""

    model_config = ConfigDict(from_attributes=True)

    enabled: bool
    updated_at: datetime


class ScanDiscoveryApiRequest(BaseModel):
    """Carry the body that scans a catalog or one namespace."""

    model_config = ConfigDict(extra="forbid")

    catalog: str
    namespace: str | None = None


class ScanDiscoveryApiResponse(BaseModel):
    """Describe what a scan registered."""

    model_config = ConfigDict(from_attributes=True)

    registered: int
    renamed: int
    dropped: int
    skipped: int
