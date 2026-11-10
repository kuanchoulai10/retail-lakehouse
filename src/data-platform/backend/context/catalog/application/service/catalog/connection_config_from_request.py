"""Define the connection_config_from_request function."""

from __future__ import annotations

from typing import Any

from base.model import validation_message
from context.catalog.application.domain.model.catalog import ConnectionConfig
from context.catalog.application.exceptions import ValidationError


def connection_config_from_request(data: dict[str, Any]) -> ConnectionConfig:
    """Read a form's connection config through ``ConnectionConfig.from_primitives``, or raise ValidationError.

    A connection read back from the catalog service may lack authentication parameters, but
    a form must give them, so a config without ``authentication`` is refused. The message
    names the field under ``connection_config`` and never carries a secret.
    """
    try:
        config = ConnectionConfig.from_primitives(data)
    except ValueError as exc:
        raise ValidationError(f"connection_config.{validation_message(exc)}") from None
    if config.authentication is None:
        raise ValidationError("connection_config.authentication: Field required")
    return config
