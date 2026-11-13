"""Define the ResetTablePropertiesUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResetTablePropertiesUseCaseOutputItem:
    """One property next to its default, as after the reset; the fields are those of the property listing."""

    key: str
    current_value: str | None
    default_value: str | None
    default_source: str | None
    modified: bool
    custom: bool
    resettable: bool
    description: str | None


@dataclass(frozen=True)
class ResetTablePropertiesUseCaseOutput:
    """Carry the table's uuid, the Iceberg version the defaults belong to and the rows as saved."""

    uuid: str
    iceberg_version: str
    items: list[ResetTablePropertiesUseCaseOutputItem]
