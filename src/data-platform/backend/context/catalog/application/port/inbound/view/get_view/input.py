"""Define the GetViewUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetViewUseCaseInput(UseCaseInput):
    """Name the view by catalog, namespace parts and name."""

    catalog: str
    namespace: tuple[str, ...]
    name: str
