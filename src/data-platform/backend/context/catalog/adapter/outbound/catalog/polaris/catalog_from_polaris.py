"""Define the catalog_from_polaris function."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from context.catalog.adapter.outbound.catalog.polaris.connection_config_from_polaris import (
    connection_config_from_polaris,
)
from context.catalog.adapter.outbound.catalog.polaris.polaris_enum import polaris_enum
from context.catalog.adapter.outbound.catalog.polaris.storage_config_from_polaris import (
    storage_config_from_polaris,
)
from context.catalog.application.exceptions import CatalogUnavailableError
from context.catalog.application.port.outbound.catalog import (
    Catalog,
    CatalogId,
    CatalogType,
)

_MILLIS_PER_SECOND = 1000


def _instant(epoch_millis: int | None) -> datetime | None:
    return None if epoch_millis is None else datetime.fromtimestamp(epoch_millis / _MILLIS_PER_SECOND, UTC)


def catalog_from_polaris(body: dict[str, Any]) -> Catalog:
    """Map a Polaris management API catalog to the Catalog aggregate.

    A value this backend does not understand, such as an unknown catalog, storage,
    connection or authentication type, raises CatalogUnavailableError naming the catalog.
    """
    name = body.get("name")
    try:
        connection = body.get("connectionConfigInfo")
        return Catalog(
            id=CatalogId.of(body["name"]),
            type=polaris_enum(CatalogType, body.get("type"), "catalog type"),
            properties=dict(body.get("properties") or {}),
            storage_config=storage_config_from_polaris(body.get("storageConfigInfo") or {}),
            connection_config=connection_config_from_polaris(connection) if isinstance(connection, dict) else None,
            entity_version=int(body.get("entityVersion", 0)),
            created_at=_instant(body.get("createTimestamp")),
            updated_at=_instant(body.get("lastUpdateTimestamp")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CatalogUnavailableError(
            f"Polaris returned catalog {name} in a form this backend cannot read: {exc}"
        ) from exc
