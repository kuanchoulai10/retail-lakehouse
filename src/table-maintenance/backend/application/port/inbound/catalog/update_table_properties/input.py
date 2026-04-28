"""Define the UpdateTablePropertiesInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateTablePropertiesInput:
    """Input for the UpdateTableProperties use case.

    properties: dict mapping Iceberg property keys to new values.
    A value of None means the property should be removed.
    """

    namespace: str
    table: str
    properties: dict[str, str | None]
