"""Define the CreateViewService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.catalog.application.exceptions import ValidationError
from context.catalog.application.port.inbound.view import (
    CreateViewUseCase,
    CreateViewUseCaseInput,
    CreateViewUseCaseOutput,
)
from context.catalog.application.port.outbound.view import View
from context.catalog.application.service.view.view_id_from_parts import view_id_from_parts
from context.catalog.application.service.view.view_output_fields import view_output_fields

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.catalog.application.port.outbound.view import ViewsRepo

_MS_PER_SECOND = 1000


class CreateViewService(CreateViewUseCase):
    """Create an Iceberg view from the create view form; the catalog assigns its uuid."""

    def __init__(
        self,
        views_repo: ViewsRepo,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo and the clock that stamps the view's first version."""
        self._views_repo = views_repo
        self._clock = clock

    def execute(self, request: CreateViewUseCaseInput) -> CreateViewUseCaseOutput:
        """Validate the form, create the view with one version and return it as the catalog saved it."""
        view_id = view_id_from_parts(request.catalog, request.namespace, request.name)
        if not request.query.strip():
            raise ValidationError("a view needs a query")
        if not request.dialect.strip():
            raise ValidationError("a view needs a sql dialect")
        view = View.define(
            id=view_id,
            query=request.query,
            dialect=request.dialect.strip(),
            default_namespace=view_id.namespace,
            timestamp_ms=int(self._clock().timestamp() * _MS_PER_SECOND),
        )
        return CreateViewUseCaseOutput(**view_output_fields(self._views_repo.create(view)))
