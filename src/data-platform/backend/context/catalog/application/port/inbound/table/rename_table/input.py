"""Define the RenameTableUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class RenameTableUseCaseInput(UseCaseInput):
    """Name the table and where it goes: ``target_namespace`` (parts) and ``target_name`` in the same catalog."""

    catalog: str
    namespace: tuple[str, ...]
    name: str
    target_namespace: tuple[str, ...]
    target_name: str
