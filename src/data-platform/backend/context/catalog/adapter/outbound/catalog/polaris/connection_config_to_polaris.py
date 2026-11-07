"""Define the connection_config_to_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.catalog.polaris.polaris_authentication_fields import (
    POLARIS_AUTHENTICATION_FIELDS,
)
from context.catalog.adapter.outbound.catalog.polaris.polaris_connection_types import (
    POLARIS_CONNECTION_TYPES,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.catalog import ConnectionConfig


def connection_config_to_polaris(config: ConnectionConfig) -> dict[str, Any]:
    """Return Polaris's ``connectionConfigInfo``, secrets included: Polaris needs them to connect."""
    info: dict[str, Any] = {"connectionType": POLARIS_CONNECTION_TYPES[config.connection_type]}
    if config.uri is not None:
        info["uri"] = config.uri
    authentication = config.authentication
    if authentication is not None:
        parameters: dict[str, Any] = {"authenticationType": authentication.authentication_type.value}
        for field, key in POLARIS_AUTHENTICATION_FIELDS.items():
            value = getattr(authentication, field)
            if value is None or value == ():
                continue
            parameters[key] = list(value) if isinstance(value, tuple) else value
        info["authenticationParameters"] = parameters
    return info
