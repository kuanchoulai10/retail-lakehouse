"""Define the UpdateTablePropertiesOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateTablePropertiesOutput:
    """Output for the UpdateTableProperties use case."""

    properties: dict[str, str]
