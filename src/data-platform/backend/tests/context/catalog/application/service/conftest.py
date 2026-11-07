"""Shared fixtures for the catalog application service tests."""

from __future__ import annotations

import pytest

from tests.context.catalog.fakes.in_memory_catalogs_repo import InMemoryCatalogsRepo
from tests.context.catalog.fakes.recording_create_catalog_content_grant_gateway import (
    RecordingCreateCatalogContentGrantGateway,
)


@pytest.fixture
def catalogs_repo() -> InMemoryCatalogsRepo:
    """Provide an empty in-memory catalogs repo."""
    return InMemoryCatalogsRepo()


@pytest.fixture
def content_grant_gateway() -> RecordingCreateCatalogContentGrantGateway:
    """Provide a content grant gateway that records and succeeds."""
    return RecordingCreateCatalogContentGrantGateway()
