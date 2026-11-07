"""Define the GetViewUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.view.get_view.input import (
    GetViewUseCaseInput,
)
from context.catalog.application.port.inbound.view.get_view.output import (
    GetViewUseCaseOutput,
)


class GetViewUseCase(UseCase[GetViewUseCaseInput, GetViewUseCaseOutput]):
    """Get one Iceberg view with its sql, schema, versions and properties."""

    @abstractmethod
    def execute(self, request: GetViewUseCaseInput) -> GetViewUseCaseOutput:
        """Get one Iceberg view with its sql, schema, versions and properties."""
