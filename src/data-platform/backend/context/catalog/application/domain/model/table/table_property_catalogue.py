"""Define the TablePropertyCatalogue value object."""

from __future__ import annotations

from typing import Self

from pydantic import field_validator, model_validator

from base import ValueObject
from context.catalog.application.domain.model.table.table_property_definition import (
    TablePropertyDefinition,
)


class TablePropertyCatalogue(ValueObject):
    """The Iceberg table properties the platform knows, with the defaults of one Iceberg version.

    Defaults change between Iceberg versions, so the catalogue names the version they come
    from; update both together when the platform upgrades Iceberg.
    """

    iceberg_version: str
    definitions: tuple[TablePropertyDefinition, ...]

    @field_validator("iceberg_version")
    @classmethod
    def _version_is_named(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("the catalogue must name the Iceberg version of its defaults")
        return value

    @model_validator(mode="after")
    def _keys_are_unique(self) -> Self:
        keys = [definition.key for definition in self.definitions]
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        if duplicates:
            raise ValueError(f"table property keys appear more than once: {', '.join(duplicates)}")
        return self

    def definition_of(self, key: str) -> TablePropertyDefinition | None:
        """Return the definition of ``key``, or None for a key the catalogue does not know."""
        return next((definition for definition in self.definitions if definition.key == key), None)
