"""Define the ReadTableMetadataGatewayListInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadTableMetadataGatewayListInput:
    """Select the catalog, and optionally one dot-joined namespace, to list."""

    catalog: str
    namespace: str | None = None
