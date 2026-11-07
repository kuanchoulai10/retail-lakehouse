"""Define the SchemaFieldApiResponse DTO."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SchemaFieldApiResponse(BaseModel):
    """One top-level column of a schema; ``type`` is text."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    required: bool
    doc: str | None
