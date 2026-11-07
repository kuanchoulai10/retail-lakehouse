"""Define the GetViewUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetViewUseCaseInput:
    """Name the view by catalog, namespace parts and name."""

    catalog: str
    namespace: list[str]
    name: str
