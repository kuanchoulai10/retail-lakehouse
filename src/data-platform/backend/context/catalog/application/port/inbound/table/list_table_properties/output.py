"""Define the ListTablePropertiesUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListTablePropertiesUseCaseOutputItem:
    """One property next to its default.

    ``default_source`` is ``iceberg``, ``catalog`` (the catalog's ``table-default.<key>``),
    ``catalog_override`` (its ``table-override.<key>``, never resettable) or None for a custom
    key without a catalog default. ``modified`` is a key the table sets to something other than
    its default, or a custom key it sets.
    """

    key: str
    current_value: str | None
    default_value: str | None
    default_source: str | None
    modified: bool
    custom: bool
    resettable: bool
    description: str | None


@dataclass(frozen=True)
class ListTablePropertiesUseCaseOutput:
    """Carry the table's uuid, the Iceberg version the defaults belong to and the rows ordered by key."""

    uuid: str
    iceberg_version: str
    items: list[ListTablePropertiesUseCaseOutputItem]
