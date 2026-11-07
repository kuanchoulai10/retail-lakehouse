"""Define the GetTableMetadataUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetTableMetadataUseCaseInput:
    """Carry the request to get the catalog metadata of one table."""

    uuid: str
