"""Test the ListTablesService."""

from __future__ import annotations

from unittest.mock import MagicMock

from application.service.catalog.list_tables import ListTablesService
from application.port.inbound.catalog.list_tables import (
    ListTablesInput,
    ListTablesOutput,
    ListTablesUseCase,
)


def test_implements_use_case():
    """ListTablesService implements ListTablesUseCase."""
    assert issubclass(ListTablesService, ListTablesUseCase)


def test_returns_tables():
    """Service delegates to reader and returns output."""
    reader = MagicMock()
    reader.list_tables.return_value = ["orders", "products"]
    service = ListTablesService(reader)

    result = service.execute(ListTablesInput(namespace="default"))

    assert isinstance(result, ListTablesOutput)
    assert result.tables == ["orders", "products"]
    reader.list_tables.assert_called_once_with("default")
