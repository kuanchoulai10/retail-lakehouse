"""Define the Namespace aggregate root."""

from __future__ import annotations

from dataclasses import dataclass

from base import AggregateRoot
from context.catalog.application.domain.model.namespace.namespace_id import NamespaceId


@dataclass(eq=False)
class Namespace(AggregateRoot[NamespaceId]):
    """A namespace: a named level inside a catalog that groups tables, views and child namespaces.

    A namespace listed from its parent carries no properties; load it by id to read them.
    """

    id: NamespaceId
    properties: dict[str, str]

    @property
    def catalog(self) -> str:
        """Return the name of the catalog holding the namespace."""
        return self.id.catalog

    @property
    def parts(self) -> tuple[str, ...]:
        """Return the parts of the namespace, outermost first."""
        return self.id.parts
