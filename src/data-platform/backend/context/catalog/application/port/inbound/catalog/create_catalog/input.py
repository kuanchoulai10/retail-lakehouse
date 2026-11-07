"""Define the CreateCatalogUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CreateCatalogUseCaseInput:
    """Carry the create catalog form.

    ``type`` is ``INTERNAL`` or ``EXTERNAL``. ``storage_config`` holds the storage fields by
    their snake_case names: ``storage_type`` is required, the rest are optional.
    """

    name: str
    type: str
    default_base_location: str
    storage_config: dict[str, Any]
