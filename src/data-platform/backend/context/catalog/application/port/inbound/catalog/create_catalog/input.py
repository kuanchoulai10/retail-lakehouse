"""Define the CreateCatalogUseCaseInput."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from base import UseCaseInput

if TYPE_CHECKING:
    from collections.abc import Iterator


class CreateCatalogUseCaseInput(UseCaseInput):
    """Carry the create catalog form.

    ``type`` is ``INTERNAL`` or ``EXTERNAL``. ``storage_config`` holds the storage fields by
    their snake_case names: ``storage_type`` is required, the rest are optional.
    ``connection_config`` (``connection_type``, ``uri`` and an ``authentication`` dict with
    ``authentication_type`` and that type's fields) is required for, and only allowed on, an
    EXTERNAL catalog. It may carry secrets, so ``repr`` leaves it out.
    """

    name: str
    type: str
    default_base_location: str
    storage_config: dict[str, Any]
    connection_config: dict[str, Any] | None = None

    def __repr_args__(self) -> Iterator[tuple[str | None, Any]]:
        """Leave ``connection_config`` out of ``repr`` and ``str``: it may carry secrets."""
        return ((name, value) for name, value in super().__repr_args__() if name != "connection_config")
