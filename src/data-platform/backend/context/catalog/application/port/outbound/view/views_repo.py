"""Define the ViewsRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.catalog.application.domain.model.view import View

if TYPE_CHECKING:
    from base import EntityId
    from context.catalog.application.domain.model.namespace import NamespaceId
    from context.catalog.application.domain.model.view import ViewId


class ViewsRepo(Repository[View]):
    """Load and save Iceberg View aggregates in the catalog service, which holds them.

    ``create`` takes a view from ``View.define`` and returns it as the catalog saved it, with
    its uuid; it raises ConflictError when the name is taken and NotFoundError when the
    namespace does not exist. ``get`` returns None for an unknown view. ``list_all`` returns
    every view of every catalog.
    """

    @abstractmethod
    def list_in(self, namespace: NamespaceId) -> list[ViewId]:
        """Return the ids of the views directly in ``namespace``; NotFoundError for an unknown namespace."""

    @abstractmethod
    def delete(self, entity_id: EntityId) -> None:
        """Drop the view from the catalog; NotFoundError for an unknown one."""
