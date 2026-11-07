"""Define the CreateNamespaceUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CreateNamespaceUseCaseInput:
    """Carry the create namespace form.

    ``namespace`` is the parts of the new namespace, outermost first; its parent must exist.
    """

    catalog: str
    namespace: list[str]
    properties: dict[str, str] = field(default_factory=dict)
