"""Define the UpdateTablePropertiesUseCaseOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateTablePropertiesUseCaseOutput:
    """Output for the UpdateTableProperties use case."""

    properties: dict[str, str]
