"""Define the CreateNamespaceUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class CreateNamespaceUseCaseInput(UseCaseInput):
    """Carry the create namespace form.

    ``namespace`` is the parts of the new namespace, outermost first; its parent must exist.
    """

    catalog: str
    namespace: tuple[str, ...]
    properties: dict[str, str] = {}
