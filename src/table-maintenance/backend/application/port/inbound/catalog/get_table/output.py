"""Define the GetTableOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetTableSchemaFieldOutput:
    """A single field in the schema output."""

    field_id: int
    name: str
    field_type: str
    required: bool


@dataclass(frozen=True)
class GetTableSchemaOutput:
    """Schema portion of the GetTable output."""

    fields: list[GetTableSchemaFieldOutput]


@dataclass(frozen=True)
class GetTableOutput:
    """Output for the GetTable use case."""

    name: str
    namespace: str
    location: str
    current_snapshot_id: int | None
    schema: GetTableSchemaOutput
    properties: dict[str, str]
