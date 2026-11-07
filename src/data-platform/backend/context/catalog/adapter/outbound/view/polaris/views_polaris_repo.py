"""Define the ViewsPolarisRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from context.catalog.adapter.outbound.shared.polaris import (
    iceberg_namespace_path,
    listed_identifiers,
    walk_iceberg_namespaces,
)
from context.catalog.adapter.outbound.view.polaris.view_from_polaris import view_from_polaris
from context.catalog.adapter.outbound.view.polaris.view_to_polaris import view_to_polaris
from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.port.outbound.view import NamespaceId, View, ViewId, ViewsRepo

if TYPE_CHECKING:
    from base import EntityId
    from context.catalog.adapter.outbound.shared.polaris import PolarisHttpClient


def _views_path(catalog: str, namespace: tuple[str, ...]) -> str:
    return f"{iceberg_namespace_path(catalog, namespace)}/views"


def _view_path(view_id: ViewId) -> str:
    return f"{_views_path(view_id.catalog, view_id.namespace)}/{quote(view_id.name, safe='')}"


class ViewsPolarisRepo(ViewsRepo):
    """Load and save Iceberg views through the Iceberg REST API of Polaris; nothing is cached."""

    def __init__(self, polaris: PolarisHttpClient) -> None:
        """Bind the Polaris client."""
        self._polaris = polaris

    def create(self, entity: View) -> View:
        """POST the name, schema, view version and properties; return the view Polaris created."""
        response = self._polaris.catalog_request(
            "POST", _views_path(entity.id.catalog, entity.id.namespace), json=view_to_polaris(entity)
        )
        return view_from_polaris(entity.id, response)

    def get(self, entity_id: EntityId) -> View | None:
        """GET the view; Polaris's 404 means there is none."""
        view_id = ViewId(entity_id.value)
        try:
            response = self._polaris.catalog_request("GET", _view_path(view_id))
        except NotFoundError:
            return None
        return view_from_polaris(view_id, response)

    def list_in(self, namespace: NamespaceId) -> list[ViewId]:
        """GET the identifiers of the namespace's views; a paged reply is refused."""
        response = self._polaris.catalog_request("GET", _views_path(namespace.catalog, namespace.parts))
        found = listed_identifiers(response, f"the views of namespace {list(namespace.parts)}")
        return [ViewId.of(namespace.catalog, parts, name) for parts, name in found]

    def list_all(self) -> list[View]:
        """Walk every namespace of every catalog and load each of its views."""
        found: list[View] = []
        for catalog, parts in walk_iceberg_namespaces(self._polaris):
            for view_id in self.list_in(NamespaceId.of(catalog, parts)):
                view = self.get(view_id)
                if view is not None:
                    found.append(view)
        return found

    def delete(self, entity_id: EntityId) -> None:
        """DELETE the view."""
        self._polaris.catalog_request("DELETE", _view_path(ViewId(entity_id.value)))
