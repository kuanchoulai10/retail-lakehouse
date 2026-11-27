"""Define the ReadTableMetadataGatewayListInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadTableMetadataGatewayListInput:
    """Select the catalog, and optionally one dot-joined namespace, whose tables and those under it to list."""

    catalog: str
    namespace: str | None = None
