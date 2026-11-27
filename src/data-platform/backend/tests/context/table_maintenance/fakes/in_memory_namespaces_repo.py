"""Define the InMemoryNamespacesRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import ConcurrentUpdateError, ConflictError
from context.table_maintenance.application.port.outbound.namespace import NamespacesRepo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from base import EntityId
    from context.table_maintenance.application.port.outbound.namespace import Namespace


class InMemoryNamespacesRepo(NamespacesRepo):
    """Keep namespaces in a dict keyed by id, saving each under compare-and-set as the SQL adapter does.

    Lists run by catalog and then by id, the order the SQL adapter gives: the id joins the levels
    with U+001F, below every printable character, so a parent comes before the namespaces under it.
    """

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, Namespace] = {}

    def create(self, entity: Namespace) -> Namespace:
        """Insert a namespace; a stored id raises ConflictError."""
        if entity.id.value in self.items:
            raise ConflictError(f"namespace {entity.id.value!r} exists")
        self.items[entity.id.value] = entity.model_copy(deep=True)
        return entity

    def get(self, entity_id: EntityId) -> Namespace | None:
        """Return a copy of the stored namespace, or None."""
        stored = self.items.get(entity_id.value)
        return None if stored is None else stored.model_copy(deep=True)

    def get_many(self, ids: Sequence[EntityId]) -> list[Namespace]:
        """Return copies of the stored namespaces among the ids."""
        wanted = {i.value for i in ids}
        return [n for n in self.list_all() if n.id.value in wanted]

    def list_all(self) -> list[Namespace]:
        """Return copies of every namespace, by catalog and id."""
        ordered = sorted(self.items.values(), key=lambda n: (n.catalog, n.id.value))
        return [n.model_copy(deep=True) for n in ordered]

    def list_in_catalog(self, catalog: str) -> list[Namespace]:
        """Return copies of the namespaces of ``catalog``, by id."""
        return [n for n in self.list_all() if n.catalog == catalog]

    def update(self, namespace: Namespace) -> Namespace:
        """Store a copy at the next version when the stored one is at the namespace's version; return it."""
        stored = self.items.get(namespace.id.value)
        described = f"namespace {'.'.join(namespace.levels)} of {namespace.catalog}"
        if stored is None:
            raise LookupError(f"{described} does not exist")
        if stored.version != namespace.version:
            raise ConcurrentUpdateError(f"{described} was changed by someone else")
        saved = namespace.model_copy(deep=True, update={"version": namespace.version + 1})
        self.items[namespace.id.value] = saved
        return saved.model_copy(deep=True)
