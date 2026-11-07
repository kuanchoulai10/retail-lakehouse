"""Define the connection_config_to_dict function."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from context.catalog.application.domain.model.catalog import ConnectionConfig

_SECRETS = frozenset({"client_secret", "bearer_token"})


def connection_config_to_dict(config: ConnectionConfig | None) -> dict[str, Any] | None:
    """Return the connection by its snake_case fields, never its secrets; None stays None."""
    if config is None:
        return None
    authentication = config.authentication
    described: dict[str, Any] | None = None
    if authentication is not None:
        described = {name: value for name, value in asdict(authentication).items() if name not in _SECRETS}
        described["authentication_type"] = authentication.authentication_type.value
        described["scopes"] = list(authentication.scopes)
    return {"connection_type": config.connection_type.value, "uri": config.uri, "authentication": described}
