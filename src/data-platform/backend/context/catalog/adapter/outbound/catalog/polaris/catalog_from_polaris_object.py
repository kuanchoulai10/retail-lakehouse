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


def _integer(value: object, what: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{what} must be an integer, not {value!r}")
    return value


def _instant(epoch_millis: object, what: str) -> datetime | None:
    if epoch_millis is None:
        return None
    return datetime.fromtimestamp(_integer(epoch_millis, what) / _MILLIS_PER_SECOND, UTC)


def _properties(value: Any) -> dict[str, str]:  # noqa: ANN401
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(f"catalog properties must be an object, not {value!r}")
    return dict(value)


def catalog_from_polaris_object(body: Any) -> Catalog:  # noqa: ANN401
    """Map one Polaris management API catalog object to the Catalog aggregate.

    ``name``, ``type``, ``storageConfigInfo`` and ``entityVersion`` are required and never
    defaulted, and nothing is coerced: a version or timestamp that is not an integer (a bool
    is not one), or properties that are not an object, raise TypeError. A missing or unknown
    value raises KeyError, TypeError or ValueError for the caller's ``read_polaris_reply`` to
    turn into a CatalogUnavailableError.
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
        properties=_properties(body.get("properties")),
        storage_config=storage_config_from_polaris(body["storageConfigInfo"]),
        connection_config=connection_config_from_polaris(connection) if isinstance(connection, dict) else None,
        entity_version=_integer(body["entityVersion"], "entityVersion"),
        created_at=_instant(body.get("createTimestamp"), "createTimestamp"),
        updated_at=_instant(body.get("lastUpdateTimestamp"), "lastUpdateTimestamp"),
    )
