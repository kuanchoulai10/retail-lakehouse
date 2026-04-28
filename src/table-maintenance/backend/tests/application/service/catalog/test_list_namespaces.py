"""Test the ListNamespacesService."""

from __future__ import annotations

from unittest.mock import MagicMock

from application.service.catalog.list_namespaces import (
    ListNamespacesService,
)
from application.port.inbound.catalog.list_namespaces import (
    ListNamespacesUseCaseInput,
    ListNamespacesUseCaseOutput,
    ListNamespacesUseCase,
)


def test_implements_use_case():
    """ListNamespacesService implements ListNamespacesUseCase."""
    assert issubclass(ListNamespacesService, ListNamespacesUseCase)


def test_returns_namespaces():
    """Service delegates to reader and returns output."""
    reader = MagicMock()
    reader.list_namespaces.return_value = ["default", "raw"]
    service = ListNamespacesService(reader)

    result = service.execute(ListNamespacesUseCaseInput())

    assert isinstance(result, ListNamespacesUseCaseOutput)
    assert result.namespaces == ["default", "raw"]
    reader.list_namespaces.assert_called_once()


def test_returns_empty_list():
    """Service handles empty catalog."""
    reader = MagicMock()
    reader.list_namespaces.return_value = []
    service = ListNamespacesService(reader)

    result = service.execute(ListNamespacesUseCaseInput())

    assert result.namespaces == []
