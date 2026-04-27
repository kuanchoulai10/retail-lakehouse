"""Test the ReadCatalogGateway port interface."""

from __future__ import annotations

import pytest

from base.gateway import Gateway

from application.port.outbound.catalog.read_catalog_gateway import ReadCatalogGateway


def test_cannot_be_instantiated() -> None:
    """ReadCatalogGateway cannot be instantiated."""
    with pytest.raises(TypeError):
        ReadCatalogGateway()


def test_is_gateway() -> None:
    """ReadCatalogGateway extends Gateway."""
    assert issubclass(ReadCatalogGateway, Gateway)


def test_declares_list_namespaces() -> None:
    """ReadCatalogGateway declares list_namespaces."""
    assert "list_namespaces" in ReadCatalogGateway.__abstractmethods__


def test_declares_list_tables() -> None:
    """ReadCatalogGateway declares list_tables."""
    assert "list_tables" in ReadCatalogGateway.__abstractmethods__


def test_declares_load_table() -> None:
    """ReadCatalogGateway declares load_table."""
    assert "load_table" in ReadCatalogGateway.__abstractmethods__
