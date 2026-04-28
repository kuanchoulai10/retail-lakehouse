"""Define the ListTagsUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.catalog.list_tags.input import ListTagsUseCaseInput
from application.port.inbound.catalog.list_tags.output import ListTagsUseCaseOutput


class ListTagsUseCase(UseCase[ListTagsUseCaseInput, ListTagsUseCaseOutput]):
    """List all tags for a table."""
