"""Define the DeleteViewUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class DeleteViewUseCaseInput(UseCaseInput):
    """Name the view by catalog, namespace parts and name."""

    catalog: str
    namespace: tuple[str, ...]
    name: str
