"""Application-layer exceptions; each carries the upstream message as ``str(exc)``."""

from __future__ import annotations

from context.catalog.application.exceptions.catalog_unavailable_error import (
    CatalogUnavailableError,
)
from context.catalog.application.exceptions.conflict_error import ConflictError
from context.catalog.application.exceptions.not_found_error import NotFoundError
from context.catalog.application.exceptions.permission_denied_error import (
    PermissionDeniedError,
)
from context.catalog.application.exceptions.validation_error import ValidationError

__all__ = [
    "CatalogUnavailableError",
    "ConflictError",
    "NotFoundError",
    "PermissionDeniedError",
    "ValidationError",
]
