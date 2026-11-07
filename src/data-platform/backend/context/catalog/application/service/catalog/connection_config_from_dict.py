"""Define the connection_config_from_dict function."""

from __future__ import annotations

from typing import Any

from context.catalog.application.domain.model.catalog import (
    AuthenticationParameters,
    AuthenticationType,
    ConnectionConfig,
    ConnectionType,
)
from context.catalog.application.exceptions import ValidationError

_CONNECTION_FIELDS = frozenset({"connection_type", "uri", "authentication"})
_FIELDS_BY_AUTHENTICATION: dict[AuthenticationType, frozenset[str]] = {
    AuthenticationType.OAUTH: frozenset({"token_uri", "client_id", "client_secret", "scopes"}),
    AuthenticationType.BEARER: frozenset({"bearer_token"}),
    AuthenticationType.SIGV4: frozenset(
        {"role_arn", "role_session_name", "external_id", "signing_region", "signing_name"}
    ),
    AuthenticationType.IMPLICIT: frozenset(),
}
_AUTHENTICATION_FIELDS = frozenset().union(*_FIELDS_BY_AUTHENTICATION.values())
_CONNECTION_TYPES = ", ".join(ConnectionType)
_AUTHENTICATION_TYPES = ", ".join(AuthenticationType)


def _authentication(data: dict[str, Any]) -> AuthenticationParameters:
    raw_type = data.get("authentication_type")
    if not raw_type:
        raise ValidationError("connection_config.authentication.authentication_type is required")
    try:
        authentication_type = AuthenticationType(raw_type)
    except ValueError:
        raise ValidationError(f"authentication type must be one of {_AUTHENTICATION_TYPES}, not {raw_type!r}") from None
    given = set(data) - {"authentication_type"}
    unknown = sorted(given - _AUTHENTICATION_FIELDS)
    if unknown:
        raise ValidationError(f"unknown authentication field(s): {', '.join(unknown)}")
    misplaced = sorted(given - _FIELDS_BY_AUTHENTICATION[authentication_type])
    if misplaced:
        raise ValidationError(f"{', '.join(misplaced)} does not apply to {authentication_type} authentication")
    values: dict[str, Any] = {name: data[name] for name in given}
    if "scopes" in values:
        values["scopes"] = tuple(values["scopes"] or ())
    return AuthenticationParameters(authentication_type=authentication_type, **values)


def connection_config_from_dict(data: dict[str, Any]) -> ConnectionConfig:
    """Build an external catalog's ConnectionConfig from its snake_case input fields.

    ``connection_type`` and ``authentication`` (with its ``authentication_type``) are required,
    and an authentication field must belong to the chosen authentication type.
    """
    unknown = sorted(set(data) - _CONNECTION_FIELDS)
    if unknown:
        raise ValidationError(f"unknown connection config field(s): {', '.join(unknown)}")
    raw_type = data.get("connection_type")
    if not raw_type:
        raise ValidationError("connection_config.connection_type is required")
    try:
        connection_type = ConnectionType(raw_type)
    except ValueError:
        raise ValidationError(f"connection type must be one of {_CONNECTION_TYPES}, not {raw_type!r}") from None
    authentication = data.get("authentication")
    if not isinstance(authentication, dict):
        raise ValidationError("connection_config.authentication is required")
    return ConnectionConfig(
        connection_type=connection_type,
        uri=data.get("uri"),
        authentication=_authentication(authentication),
    )
