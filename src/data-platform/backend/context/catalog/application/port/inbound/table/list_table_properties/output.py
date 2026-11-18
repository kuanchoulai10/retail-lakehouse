"""Define the ListTablePropertiesUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class ListTablePropertiesUseCaseOutput(UseCaseOutput):
    """Carry the table's uuid, the Iceberg version the defaults belong to and the rows ordered by key."""

    class Property(UseCaseOutput):
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

    uuid: str
    iceberg_version: str
    items: tuple[Property, ...]
