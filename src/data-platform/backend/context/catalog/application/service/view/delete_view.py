"""Define the DeleteViewService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.port.inbound.view import (
    DeleteViewUseCase,
    DeleteViewUseCaseInput,
    DeleteViewUseCaseOutput,
)
from context.catalog.application.service.view.view_id_from_parts import view_id_from_parts

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.view import ViewsRepo


class DeleteViewService(DeleteViewUseCase):
    """Drop an Iceberg view from the catalog."""

    def __init__(self, views_repo: ViewsRepo) -> None:
        """Bind the repo."""
        self._views_repo = views_repo

    def execute(self, request: DeleteViewUseCaseInput) -> DeleteViewUseCaseOutput:
        """Drop the view; the repo raises NotFoundError for an unknown one."""
        self._views_repo.delete(view_id_from_parts(request.catalog, request.namespace, request.name))
        return DeleteViewUseCaseOutput()
