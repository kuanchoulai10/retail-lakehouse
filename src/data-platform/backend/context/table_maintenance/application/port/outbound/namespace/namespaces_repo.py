"""Define the NamespacesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.table_maintenance.application.domain.model.namespace import Namespace

if TYPE_CHECKING:
    from collections.abc import Sequence

    from base import EntityId


class NamespacesRepo(Repository[Namespace]):
    """Persist the policies attached to each namespace, one record per catalog and levels.

    ``create`` raises ``ConflictError`` for a namespace already stored, and ``list_all`` lists by
    catalog and then by levels, a parent before the namespaces under it.
    """

    @abstractmethod
    def get_many(self, ids: Sequence[EntityId]) -> list[Namespace]:
        """Return the namespaces that exist among ``ids``, in no particular order."""

    @abstractmethod
    def list_in_catalog(self, catalog: str) -> list[Namespace]:
        """Return the namespaces of ``catalog`` by levels, a parent before the namespaces under it."""

    @abstractmethod
    def update(self, namespace: Namespace) -> Namespace:
        """Persist the changed namespace when the stored one is still at its version; return it as now stored.

        The save is a compare-and-set on ``namespace.version``, as for ``CatalogsRepo.update``: a
        namespace read before another save raises ``ConcurrentUpdateError`` and changes nothing, one
        never stored raises ``LookupError``, and the namespace returned is read back at the new version.
        """
