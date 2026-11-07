"""Define the RecordingCreateCatalogContentGrantGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.port.outbound.catalog import (
    CreateCatalogContentGrantGateway,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.catalog import (
        CreateCatalogContentGrantGatewayInput,
    )


class RecordingCreateCatalogContentGrantGateway(CreateCatalogContentGrantGateway):
    """Record every grant, or raise the given error to stand for a refused grant."""

    def __init__(self, error: Exception | None = None) -> None:
        """Start with no calls; ``error`` is raised by every call when given."""
        self.calls: list[CreateCatalogContentGrantGatewayInput] = []
        self.error = error

    def create(self, input: CreateCatalogContentGrantGatewayInput) -> None:  # noqa: A002
        """Record the call, then raise the error when one was given."""
        self.calls.append(input)
        if self.error is not None:
            raise self.error
