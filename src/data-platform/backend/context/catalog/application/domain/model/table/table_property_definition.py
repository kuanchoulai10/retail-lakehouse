"""Define the TablePropertyDefinition value object."""

from __future__ import annotations

from typing import Self

from pydantic import field_validator, model_validator

from base import ValueObject


class TablePropertyDefinition(ValueObject):
    """One known Iceberg table property: its key, Iceberg's default, what it does and whether a reset may touch it.

    ``iceberg_default`` is the value Iceberg uses when the table does not set the key, as text,
    or None when Iceberg has no default (the engine or the table location decides).
    ``resettable`` is False when removing the key would change the table unsafely.
    ``written_on_create`` marks a key Iceberg writes on every new table, so that an absent key
    means an older default; a reset writes ``iceberg_default`` instead of removing the key.
    """

    key: str
    iceberg_default: str | None
    description: str
    resettable: bool = True
    written_on_create: bool = False

    @field_validator("key")
    @classmethod
    def _key_is_a_word(cls, value: str) -> str:
        if not value or any(character.isspace() for character in value):
            raise ValueError("a table property key must be non-blank and hold no whitespace")
        return value

    @field_validator("description")
    @classmethod
    def _description_is_one_line(cls, value: str) -> str:
        if not value.strip() or "\n" in value:
            raise ValueError("a table property description must be one non-blank line")
        return value

    @model_validator(mode="after")
    def _written_on_create_is_restored(self) -> Self:
        if self.written_on_create and (self.iceberg_default is None or not self.resettable):
            raise ValueError("a key written on create needs a default and must be resettable")
        return self
