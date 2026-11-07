"""Define the GetViewService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.port.inbound.view import (
    GetViewUseCase,
    GetViewUseCaseInput,
    GetViewUseCaseOutput,
)
from context.catalog.application.service.view.view_id_from_parts import view_id_from_parts
from context.catalog.application.service.view.view_output_fields import view_output_fields

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.view import ViewsRepo


class GetViewService(GetViewUseCase):
    """Get one Iceberg view with everything the view page shows."""

    def __init__(self, views_repo: ViewsRepo) -> None:
        """Bind the repo."""
        self._views_repo = views_repo

    def execute(self, request: GetViewUseCaseInput) -> GetViewUseCaseOutput:
        """Return the view or raise NotFoundError."""
        view = self._views_repo.get(view_id_from_parts(request.catalog, request.namespace, request.name))
        if view is None:
            raise NotFoundError(
                f"view {request.name} not found in namespace {request.namespace} of catalog {request.catalog}"
            )
        return GetViewUseCaseOutput(**view_output_fields(view))
