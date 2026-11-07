"""Define the catalog_from_polaris_object function."""

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
from context.catalog.application.port.outbound.catalog import (
    Catalog,
    CatalogId,
    CatalogType,
)

_MILLIS_PER_SECOND = 1000


def _instant(epoch_millis: int | None) -> datetime | None:
    return None if epoch_millis is None else datetime.fromtimestamp(epoch_millis / _MILLIS_PER_SECOND, UTC)


def catalog_from_polaris_object(body: Any) -> Catalog:  # noqa: ANN401
    """Map one Polaris management API catalog object to the Catalog aggregate.

    ``name``, ``type``, ``storageConfigInfo`` and ``entityVersion`` are required and never
    defaulted. A missing or unknown value raises KeyError, TypeError or ValueError for the
    caller's ``read_polaris_reply`` to turn into a CatalogUnavailableError.
    """
    if not isinstance(body, dict):
        raise TypeError(f"catalog must be an object, not {body!r}")
    name = body["name"]
    if not isinstance(name, str):
        raise TypeError(f"catalog name must be a string, not {name!r}")
    connection = body.get("connectionConfigInfo")
    return Catalog(
        id=CatalogId.of(name),
        type=polaris_enum(CatalogType, body["type"], "catalog type"),
        properties=dict(body.get("properties") or {}),
        storage_config=storage_config_from_polaris(body["storageConfigInfo"]),
        connection_config=connection_config_from_polaris(connection) if isinstance(connection, dict) else None,
        entity_version=int(body["entityVersion"]),
        created_at=_instant(body.get("createTimestamp")),
        updated_at=_instant(body.get("lastUpdateTimestamp")),
    )
