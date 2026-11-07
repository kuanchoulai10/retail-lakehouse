"""Define the RenameTableUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RenameTableUseCaseInput:
    """Name the table and where it goes: ``target_namespace`` (parts) and ``target_name`` in the same catalog."""

    catalog: str
    namespace: list[str]
    name: str
    target_namespace: list[str]
    target_name: str
