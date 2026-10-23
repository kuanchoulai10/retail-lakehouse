"""Define the ReadCatalogGatewayListInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadCatalogGatewayListInput:
    """Select the catalog, and optionally one dot-joined namespace, to list."""

    catalog: str
    namespace: str | None = None
