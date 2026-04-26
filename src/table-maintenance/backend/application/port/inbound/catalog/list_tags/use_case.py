"""Define the ListTagsUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.catalog.list_tags.input import ListTagsInput
from application.port.inbound.catalog.list_tags.output import ListTagsOutput


class ListTagsUseCase(UseCase[ListTagsInput, ListTagsOutput]):
    """List all tags for a table."""
