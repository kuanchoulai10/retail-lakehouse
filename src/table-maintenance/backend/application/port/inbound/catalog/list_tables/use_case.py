"""Define the ListTablesUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.catalog.list_tables.input import ListTablesUseCaseInput
from application.port.inbound.catalog.list_tables.output import ListTablesUseCaseOutput


class ListTablesUseCase(UseCase[ListTablesUseCaseInput, ListTablesUseCaseOutput]):
    """List all tables in a namespace."""
