"""Define the storage_config_from_request function."""

from __future__ import annotations

from typing import Any

from base.model import validation_message
from context.catalog.application.domain.model.catalog import StorageConfig
from context.catalog.application.exceptions import ValidationError

_ASSIGNED_BY_THE_CATALOG = "user_arn"


def storage_config_from_request(data: dict[str, Any]) -> StorageConfig:
    """Read a form's storage config through ``StorageConfig.from_primitives``, or raise ValidationError.

    ``user_arn`` is a field of the config but assigned by the catalog service, so a form that
    sets it is refused like any unknown field. The message names the field under ``storage_config``.
    """
    if _ASSIGNED_BY_THE_CATALOG in data:
        raise ValidationError(f"storage_config.{_ASSIGNED_BY_THE_CATALOG}: Extra inputs are not permitted")
    try:
        return StorageConfig.from_primitives(data)
    except ValueError as exc:
        raise ValidationError(f"storage_config.{validation_message(exc)}") from None
