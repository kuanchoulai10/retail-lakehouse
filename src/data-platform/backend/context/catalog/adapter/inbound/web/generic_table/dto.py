"""Define the generic table API DTOs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CreateGenericTableApiRequest(BaseModel):
    """Carry the create generic table form: name, format, optional base location and doc, properties."""

    model_config = ConfigDict(extra="forbid")

    name: str
    format: str
    base_location: str | None = None
    doc: str | None = None
    properties: dict[str, str] = Field(default_factory=dict)


class GenericTableApiResponse(BaseModel):
    """Describe a generic table: format, base location, doc and properties; it has no schema or snapshots."""

    model_config = ConfigDict(from_attributes=True)

    catalog: str
    namespace: list[str]
    name: str
    format: str
    base_location: str | None
    doc: str | None
    properties: dict[str, str]


class GenericTableIdentifierApiResponse(BaseModel):
    """Name a generic table in a listing."""

    model_config = ConfigDict(from_attributes=True)

    catalog: str
    namespace: list[str]
    name: str
