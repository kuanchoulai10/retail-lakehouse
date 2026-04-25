"""Define the ListTablesUseCase interface."""

from __future__ import annotations

from core.base.use_case import UseCase
from core.application.port.inbound.catalog.list_tables.input import ListTablesInput
from core.application.port.inbound.catalog.list_tables.output import ListTablesOutput


class ListTablesUseCase(UseCase[ListTablesInput, ListTablesOutput]):
    """List all tables in a namespace."""
