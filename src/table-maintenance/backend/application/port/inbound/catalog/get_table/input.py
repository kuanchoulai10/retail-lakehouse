"""Define the GetTableInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetTableInput:
    """Input for the GetTable use case."""

    namespace: str
    table: str
