"""Define the ID of the discovery schedule of a catalog."""

from __future__ import annotations

TABLE_DISCOVERY_SCHEDULE_ID_PREFIX = "table-discovery:catalog="


def table_discovery_schedule_id(catalog: str) -> str:
    """Return the ID of the discovery schedule of a catalog (one schedule per catalog)."""
    return f"{TABLE_DISCOVERY_SCHEDULE_ID_PREFIX}{catalog}"
