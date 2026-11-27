"""Define the CatalogsRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.table_maintenance.application.domain.model.catalog import Catalog

if TYPE_CHECKING:
    from collections.abc import Sequence

    from base import EntityId


class CatalogsRepo(Repository[Catalog]):
    """Persist the policies attached to each catalog, one record per catalog name.

    ``create`` raises ``ConflictError`` for a catalog already stored, and ``list_all`` lists by name.
    """

    @abstractmethod
    def get_many(self, ids: Sequence[EntityId]) -> list[Catalog]:
        """Return the catalogs that exist among ``ids``, in no particular order."""

    @abstractmethod
    def update(self, catalog: Catalog) -> Catalog:
        """Persist the changed catalog when the stored one is still at its version; return it as now stored.

        The save is a compare-and-set on ``catalog.version``: it writes only when the stored catalog
        is at that version, and moves the stored version on by one. A catalog read before another
        save raises ``ConcurrentUpdateError`` and changes nothing; a catalog never stored raises
        ``LookupError``. The catalog returned is a new object read back from storage, at the new
        version; the caller's object is left as it was.
        """
