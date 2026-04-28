"""Define the GetTableUseCaseOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetTableSchemaFieldUseCaseOutput:
    """A single field in the schema output."""

    field_id: int
    name: str
    field_type: str
    required: bool


@dataclass(frozen=True)
class GetTableSchemaUseCaseOutput:
    """Schema portion of the GetTable output."""

    fields: list[GetTableSchemaFieldUseCaseOutput]


@dataclass(frozen=True)
class GetTableUseCaseOutput:
    """Output for the GetTable use case."""

    name: str
    namespace: str
    location: str
    current_snapshot_id: int | None
    schema: GetTableSchemaUseCaseOutput
    properties: dict[str, str]
