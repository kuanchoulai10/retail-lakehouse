"""Tests for ReadCatalogIcebergGateway implementing ReadCatalogGateway."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from adapter.outbound.catalog.read_catalog_iceberg_gateway import (
    ReadCatalogIcebergGateway,
)
from application.domain.model.catalog.table import Table
from application.port.outbound.catalog.read_catalog_gateway import ReadCatalogGateway


@pytest.fixture
def mock_pyiceberg_catalog():
    """Return a mock PyIceberg catalog."""
    return MagicMock()


@pytest.fixture
def client(mock_pyiceberg_catalog):
    """Return a ReadCatalogIcebergGateway wrapping a mock catalog."""
    with patch(
        "adapter.outbound.catalog.read_catalog_iceberg_gateway.load_catalog",
        return_value=mock_pyiceberg_catalog,
    ):
        return ReadCatalogIcebergGateway(
            catalog_uri="http://polaris:8181/api/catalog",
            catalog_name="iceberg",
        )


def test_client_implements_gateway(client):
    """ReadCatalogIcebergGateway implements the ReadCatalogGateway port."""
    assert isinstance(client, ReadCatalogGateway)


def test_list_namespaces(client, mock_pyiceberg_catalog):
    """Return namespace names as a list of strings."""
    mock_pyiceberg_catalog.list_namespaces.return_value = [
        ("default",),
        ("raw",),
    ]
    result = client.list_namespaces()
    assert result == ["default", "raw"]
    mock_pyiceberg_catalog.list_namespaces.assert_called_once()


def test_list_tables(client, mock_pyiceberg_catalog):
    """Return table names as a list of strings."""
    mock_pyiceberg_catalog.list_tables.return_value = [
        ("default", "orders"),
        ("default", "products"),
    ]
    result = client.list_tables("default")
    assert result == ["orders", "products"]
    mock_pyiceberg_catalog.list_tables.assert_called_once_with(namespace="default")


def _mock_pyiceberg_table():
    """Build a mock PyIceberg table with schema, snapshots, branches, tags."""
    mock_table = MagicMock()
    mock_table.metadata.location = "s3://warehouse/default/orders"
    mock_table.metadata.current_snapshot_id = 123
    mock_table.metadata.properties = {"write.format.default": "parquet"}

    # Schema
    mock_field = MagicMock()
    mock_field.field_id = 1
    mock_field.name = "order_id"
    mock_field.field_type = MagicMock()
    mock_field.field_type.__str__ = lambda self: "long"
    mock_field.required = True
    mock_table.schema.return_value.fields = (mock_field,)

    # Snapshots
    mock_snap = MagicMock()
    mock_snap.snapshot_id = 100
    mock_snap.parent_snapshot_id = None
    mock_snap.timestamp_ms = 1713600000000
    mock_summary = MagicMock()
    mock_summary.model_dump.return_value = {
        "operation": "append",
        "added-records": "50",
    }
    mock_snap.summary = mock_summary
    mock_table.metadata.snapshots = [mock_snap]

    # Refs (branch + tag)
    main_ref = MagicMock()
    main_ref.snapshot_id = 100
    main_ref.snapshot_ref_type = "branch"
    main_ref.max_ref_age_ms = None
    main_ref.max_snapshot_age_ms = 86400000
    main_ref.min_snapshots_to_keep = 5

    tag_ref = MagicMock()
    tag_ref.snapshot_id = 100
    tag_ref.snapshot_ref_type = "tag"
    tag_ref.max_ref_age_ms = None

    mock_table.metadata.refs = {"main": main_ref, "v1.0": tag_ref}

    return mock_table


def test_load_table(client, mock_pyiceberg_catalog):
    """Return a Table domain aggregate from PyIceberg metadata."""
    mock_pyiceberg_catalog.load_table.return_value = _mock_pyiceberg_table()

    result = client.load_table("default", "orders")

    assert isinstance(result, Table)
    assert result.id.value == "default.orders"
    assert result.namespace == "default"
    assert result.name == "orders"
    assert result.location == "s3://warehouse/default/orders"
    assert result.current_snapshot_id == 123
    assert result.properties == {"write.format.default": "parquet"}

    # Schema
    assert len(result.schema.fields) == 1
    assert result.schema.fields[0].name == "order_id"
    assert result.schema.fields[0].field_type == "long"

    # Snapshots
    assert len(result.snapshots) == 1
    assert result.snapshots[0].snapshot_id == 100
    assert result.snapshots[0].parent_id is None
    assert result.snapshots[0].summary.data == {
        "operation": "append",
        "added-records": "50",
    }

    # Branches
    assert len(result.branches) == 1
    assert result.branches[0].id.value == "main"
    assert result.branches[0].snapshot_id == 100
    assert result.branches[0].retention.max_snapshot_age_ms == 86400000
    assert result.branches[0].retention.min_snapshots_to_keep == 5

    # Tags
    assert len(result.tags) == 1
    assert result.tags[0].name == "v1.0"
    assert result.tags[0].snapshot_id == 100


def test_list_namespaces_not_found(client, mock_pyiceberg_catalog):
    """Raise NoSuchNamespaceError when catalog returns an error."""
    from pyiceberg.exceptions import NoSuchNamespaceError

    mock_pyiceberg_catalog.list_namespaces.side_effect = NoSuchNamespaceError("nope")
    with pytest.raises(NoSuchNamespaceError):
        client.list_namespaces()


def test_load_table_not_found(client, mock_pyiceberg_catalog):
    """Raise NoSuchTableError when table does not exist."""
    from pyiceberg.exceptions import NoSuchTableError

    mock_pyiceberg_catalog.load_table.side_effect = NoSuchTableError("nope")
    with pytest.raises(NoSuchTableError):
        client.load_table("default", "nonexistent")
