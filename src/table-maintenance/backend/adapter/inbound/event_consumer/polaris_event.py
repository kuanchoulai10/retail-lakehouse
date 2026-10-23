"""Define the PolarisEvent adapter DTO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolarisEvent:
    """Carry the fields of a Polaris Kafka event that the consumer reads.

    ``destination`` is the rename target as ``[*namespace_levels, table]``.
    """

    event_type: str
    catalog_name: str
    namespace: list[str]
    table_name: str | None
    event_id: str | None
    destination: list[str] | None = None
