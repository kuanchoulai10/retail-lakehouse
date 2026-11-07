"""Define the SchemaApiResponse DTO."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from context.catalog.adapter.inbound.web.shared.schema_field_api_response import SchemaFieldApiResponse


class SchemaApiResponse(BaseModel):
    """A schema: its id and its top-level fields, as a table or a view carries it."""

    model_config = ConfigDict(from_attributes=True)

    schema_id: int
    fields: list[SchemaFieldApiResponse]
