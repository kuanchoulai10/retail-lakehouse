"""Define the IncludeTableUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IncludeTableUseCaseInput:
    """Carry the request to include a table in maintenance by hand."""

    catalog: str
    namespace: str
    table: str
    preset_id: str
