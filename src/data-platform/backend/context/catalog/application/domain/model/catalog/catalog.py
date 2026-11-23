"""Define the Catalog aggregate root."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from base import AggregateRoot, ReadOnlyMapping
from context.catalog.application.domain.model.catalog.catalog_id import CatalogId
from context.catalog.application.domain.model.catalog.catalog_type import CatalogType
from context.catalog.application.domain.model.catalog.connection_config import ConnectionConfig
from context.catalog.application.domain.model.catalog.storage_config import StorageConfig

if TYPE_CHECKING:
    from collections.abc import Mapping

_DEFAULT_BASE_LOCATION = "default-base-location"
_TABLE_DEFAULT_PREFIX = "table-default."
_TABLE_OVERRIDE_PREFIX = "table-override."


def _with_prefix(properties: Mapping[str, str], prefix: str) -> dict[str, str]:
    return {
        key.removeprefix(prefix): value for key, value in properties.items() if key.startswith(prefix) and key != prefix
    }


class Catalog(AggregateRoot[CatalogId]):
    """A catalog: a named, versioned container of namespaces, kept by the catalog service.

    ``entity_version`` is the version this copy was loaded at; a save is rejected when the
    stored catalog has moved past it. A catalog not yet saved has version 0 and no timestamps.
    The ``default-base-location`` property is where new tables go when they name no location.
    ``table-default.<key>`` and ``table-override.<key>`` properties are applied to a table
    when it is created (the override wins over what the create asks for); never afterwards.
    ``connection_config`` is the remote catalog service an EXTERNAL catalog mirrors, if any;
    an INTERNAL catalog has none.
    """

    id: CatalogId
    type: CatalogType
    properties: ReadOnlyMapping[str, str]
    storage_config: StorageConfig
    connection_config: ConnectionConfig | None = None
    entity_version: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        id: CatalogId,  # noqa: A002
        type: CatalogType,  # noqa: A002
        default_base_location: str,
        storage_config: StorageConfig,
        connection_config: ConnectionConfig | None = None,
    ) -> Catalog:
        """Return a new, unsaved catalog whose only property is its default base location."""
        return cls(
            id=id,
            type=type,
            properties={_DEFAULT_BASE_LOCATION: default_base_location},
            storage_config=storage_config,
            connection_config=connection_config,
        )

    @property
    def name(self) -> str:
        """Return the catalog name."""
        return self.id.name

    @property
    def default_base_location(self) -> str | None:
        """Return the default base location, or None when the property is missing."""
        return self.properties.get(_DEFAULT_BASE_LOCATION)

    @property
    def table_property_defaults(self) -> dict[str, str]:
        """Return the table properties the catalog gives a new table unless it sets them (``table-default.<key>``)."""
        return _with_prefix(self.properties, _TABLE_DEFAULT_PREFIX)

    @property
    def table_property_overrides(self) -> dict[str, str]:
        """Return the table properties the catalog forces on a new table (``table-override.<key>``)."""
        return _with_prefix(self.properties, _TABLE_OVERRIDE_PREFIX)

    def reconfigure(
        self,
        *,
        default_base_location: str,
        properties: dict[str, str],
        storage_config: StorageConfig,
        loaded_version: int,
    ) -> None:
        """Replace the properties and storage config, as a change made to ``loaded_version``.

        ``default_base_location`` wins over a ``default-base-location`` entry in ``properties``.
        The three fields change together: when one is invalid, none changes.
        """
        self._assign_together(
            properties={**properties, _DEFAULT_BASE_LOCATION: default_base_location},
            storage_config=storage_config,
            entity_version=loaded_version,
        )
