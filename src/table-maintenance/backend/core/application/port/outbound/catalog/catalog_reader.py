"""Define the CatalogReader port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.application.domain.model.catalog.table import Table


class CatalogReader(ABC):
    """Read-only port for accessing Iceberg catalog metadata.

    Not a Repository because this is a remote catalog, not our own persistence.
    """

    @abstractmethod
    def list_namespaces(self) -> list[str]:
        """Return all namespace names in the catalog."""

    @abstractmethod
    def list_tables(self, namespace: str) -> list[str]:
        """Return all table names within a namespace."""

    @abstractmethod
    def load_table(self, namespace: str, table: str) -> Table:
        """Load the full Table aggregate from the catalog."""
