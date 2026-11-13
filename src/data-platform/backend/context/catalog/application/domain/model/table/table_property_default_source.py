"""Define the TablePropertyDefaultSource enum."""

from __future__ import annotations

from enum import StrEnum


class TablePropertyDefaultSource(StrEnum):
    """Where a table property's default comes from.

    ``iceberg`` is Iceberg's own default; ``catalog`` is the catalog's ``table-default.<key>``;
    ``catalog_override`` is the catalog's ``table-override.<key>``, which the catalog forces
    on every new table.
    """

    ICEBERG = "iceberg"
    CATALOG = "catalog"
    CATALOG_OVERRIDE = "catalog_override"
