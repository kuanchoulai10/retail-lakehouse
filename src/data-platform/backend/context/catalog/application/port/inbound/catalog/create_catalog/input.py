"""Define the CreateCatalogUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CreateCatalogUseCaseInput:
    """Carry the create catalog form.

    ``type`` is ``INTERNAL`` or ``EXTERNAL``. ``storage_config`` holds the storage fields by
    their snake_case names: ``storage_type`` is required, the rest are optional.
    ``connection_config`` (``connection_type``, ``uri`` and an ``authentication`` dict with
    ``authentication_type`` and that type's fields) is required for, and only allowed on, an
    EXTERNAL catalog.
    """

    name: str
    type: str
    default_base_location: str
    storage_config: dict[str, Any]
    connection_config: dict[str, Any] | None = None
