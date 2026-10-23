"""Define the policy template API DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreatePolicyTemplateApiRequest(BaseModel):
    """Carry the body that creates a policy template."""

    model_config = ConfigDict(extra="forbid")

    name: str
    settings: dict[str, Any] = Field(default_factory=dict)


class UpdatePolicyTemplateApiRequest(BaseModel):
    """Carry the body that changes a policy template; omitted fields stay."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    settings: dict[str, Any] | None = None


class PolicyTemplateApiResponse(BaseModel):
    """Describe a policy template."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime
