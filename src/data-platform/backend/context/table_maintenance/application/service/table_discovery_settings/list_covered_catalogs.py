"""Define the ListCoveredCatalogsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.inbound.table_discovery_settings import (
    ListCoveredCatalogsUseCase,
    ListCoveredCatalogsUseCaseInput,
    ListCoveredCatalogsUseCaseOutput,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class ListCoveredCatalogsService(ListCoveredCatalogsUseCase):
    """List the catalogs maintenance covers."""

    def __init__(self, catalog_names: Sequence[str]) -> None:
        """Bind the configured catalog names."""
        self._catalog_names = tuple(catalog_names)

    def execute(
        self,
        request: ListCoveredCatalogsUseCaseInput,  # noqa: ARG002
    ) -> ListCoveredCatalogsUseCaseOutput:
        """Return the configured catalog names in order."""
        return ListCoveredCatalogsUseCaseOutput(catalogs=list(self._catalog_names))
