"""Define the CatalogId identifier."""

from __future__ import annotations

from base import EntityId
from context.catalog.application.domain.model.shared import reject_unit_separator


class CatalogId(EntityId):
    """Identify a catalog by its name, which is unique within the catalog service."""

    @classmethod
    def of(cls, name: str) -> CatalogId:
        """Return the id of the catalog called ``name``; ValueError when it holds U+001F."""
        reject_unit_separator("catalog name", name)
        return cls(name)

    @property
    def name(self) -> str:
        """Return the catalog name."""
        return self.value
