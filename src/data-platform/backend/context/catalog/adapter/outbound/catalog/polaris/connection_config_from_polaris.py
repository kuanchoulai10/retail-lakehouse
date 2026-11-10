"""Define the connection_config_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.catalog.polaris.polaris_authentication_fields import (
    POLARIS_AUTHENTICATION_FIELDS,
)
from context.catalog.adapter.outbound.catalog.polaris.polaris_connection_types import (
    POLARIS_CONNECTION_TYPES,
)
from context.catalog.adapter.outbound.catalog.polaris.polaris_enum import polaris_enum
from context.catalog.application.port.outbound.catalog import (
    AuthenticationParameters,
    AuthenticationType,
    ConnectionConfig,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.catalog import ConnectionType

_SECRETS = frozenset({"client_secret", "bearer_token"})
_CONNECTION_TYPES = {wire: connection_type for connection_type, wire in POLARIS_CONNECTION_TYPES.items()}


def _connection_type(wire: object) -> ConnectionType:
    connection_type = _CONNECTION_TYPES.get(wire) if isinstance(wire, str) else None
    if connection_type is None:
        raise ValueError(f"unknown connection type {wire!r}")
    return connection_type


def _authentication(parameters: dict[str, Any]) -> AuthenticationParameters:
    values: dict[str, Any] = {
        field: parameters[key]
        for field, key in POLARIS_AUTHENTICATION_FIELDS.items()
        if field not in _SECRETS and parameters.get(key) is not None
    }
    if "scopes" in values:
        if not isinstance(values["scopes"], list):
            raise TypeError(f"scopes must be a list, not {values['scopes']!r}")
        values["scopes"] = tuple(values["scopes"])
    authentication_type = polaris_enum(AuthenticationType, parameters.get("authenticationType"), "authentication type")
    return AuthenticationParameters(authentication_type=authentication_type, **values)


def connection_config_from_polaris(info: dict[str, Any]) -> ConnectionConfig:
    """Map Polaris's ``connectionConfigInfo``; secrets and the read-only service identity are dropped.

    Polaris treats ``clientSecret`` and ``bearerToken`` as input-only, so a read should not
    carry them; if one ever does, it is not kept. An unknown enum value raises ValueError.
    """
    parameters = info.get("authenticationParameters")
    return ConnectionConfig(
        connection_type=_connection_type(info.get("connectionType")),
        uri=info.get("uri"),
        authentication=_authentication(parameters) if isinstance(parameters, dict) else None,
    )
