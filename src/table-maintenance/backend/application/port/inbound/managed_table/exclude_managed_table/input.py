"""Define the ExcludeManagedTableUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExcludeManagedTableUseCaseInput:
    """Carry the request to exclude a table from maintenance by hand."""

    catalog: str
    namespace: str
    table: str
