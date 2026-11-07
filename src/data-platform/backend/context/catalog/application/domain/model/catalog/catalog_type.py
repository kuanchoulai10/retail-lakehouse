"""Define the CatalogType enumeration."""

from __future__ import annotations

from enum import StrEnum


class CatalogType(StrEnum):
    """Say whether the catalog service owns a catalog's tables or mirrors another catalog."""

    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"
