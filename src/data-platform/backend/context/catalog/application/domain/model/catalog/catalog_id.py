"""Define the CatalogId identifier."""

from __future__ import annotations

from dataclasses import dataclass

from base import EntityId


@dataclass(frozen=True)
class CatalogId(EntityId):
    """Identify a catalog by its name, which is unique within the catalog service."""

    @classmethod
    def of(cls, name: str) -> CatalogId:
        """Return the id of the catalog called ``name``."""
        return cls(name)

    @property
    def name(self) -> str:
        """Return the catalog name."""
        return self.value
