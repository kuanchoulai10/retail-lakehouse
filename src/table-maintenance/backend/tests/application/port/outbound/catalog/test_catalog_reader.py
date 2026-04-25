"""Test the CatalogReader port interface."""

from __future__ import annotations

from abc import ABC

import pytest

from core.application.port.outbound.catalog.catalog_reader import CatalogReader


def test_catalog_reader_is_abstract():
    """CatalogReader cannot be instantiated."""
    with pytest.raises(TypeError):
        CatalogReader()


def test_catalog_reader_is_abc():
    """CatalogReader extends ABC."""
    assert issubclass(CatalogReader, ABC)


def test_catalog_reader_has_list_namespaces():
    """CatalogReader declares list_namespaces."""
    assert "list_namespaces" in CatalogReader.__abstractmethods__


def test_catalog_reader_has_list_tables():
    """CatalogReader declares list_tables."""
    assert "list_tables" in CatalogReader.__abstractmethods__


def test_catalog_reader_has_load_table():
    """CatalogReader declares load_table."""
    assert "load_table" in CatalogReader.__abstractmethods__
