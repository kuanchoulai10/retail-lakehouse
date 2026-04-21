"""Tests for IcebergCatalogClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient


@pytest.fixture
def mock_pyiceberg_catalog():
    """Return a mock PyIceberg catalog."""
    return MagicMock()


@pytest.fixture
def client(mock_pyiceberg_catalog):
    """Return an IcebergCatalogClient wrapping a mock catalog."""
    with patch(
        "adapter.outbound.catalog.iceberg_catalog_client.load_catalog",
        return_value=mock_pyiceberg_catalog,
    ):
        return IcebergCatalogClient(
            catalog_uri="http://polaris:8181/api/catalog",
            catalog_name="iceberg",
        )


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


def test_get_table(client, mock_pyiceberg_catalog):
    """Return table metadata as a plain dict."""
    mock_table = MagicMock()
    mock_table.metadata.current_snapshot_id = 123
    mock_table.metadata.location = "s3://warehouse/default/orders"
    mock_table.metadata.properties = {"write.format.default": "parquet"}

    mock_field = MagicMock()
    mock_field.field_id = 1
    mock_field.name = "order_id"
    mock_field.field_type = MagicMock()
    mock_field.field_type.__str__ = lambda self: "long"
    mock_field.required = True
    mock_table.schema.return_value.fields = (mock_field,)

    mock_pyiceberg_catalog.load_table.return_value = mock_table
    result = client.get_table("default", "orders")

    assert result["table"] == "orders"
    assert result["namespace"] == "default"
    assert result["location"] == "s3://warehouse/default/orders"
    assert result["current_snapshot_id"] == 123
    assert result["schema"]["fields"][0]["name"] == "order_id"
    assert result["properties"] == {"write.format.default": "parquet"}


def test_list_snapshots(client, mock_pyiceberg_catalog):
    """Return snapshots as a list of dicts."""
    mock_snap = MagicMock()
    mock_snap.snapshot_id = 100
    mock_snap.parent_snapshot_id = None
    mock_snap.timestamp_ms = 1713600000000
    mock_snap.summary = {"operation": "append", "added-records": "50"}

    mock_table = MagicMock()
    mock_table.metadata.snapshots = [mock_snap]
    mock_pyiceberg_catalog.load_table.return_value = mock_table

    result = client.list_snapshots("default", "orders")
    assert len(result) == 1
    assert result[0]["snapshot_id"] == 100
    assert result[0]["parent_id"] is None
    assert result[0]["timestamp_ms"] == 1713600000000
    assert result[0]["summary"] == {"operation": "append", "added-records": "50"}


def test_list_branches(client, mock_pyiceberg_catalog):
    """Return only branch refs."""
    main_ref = MagicMock()
    main_ref.snapshot_id = 100
    main_ref.snapshot_ref_type = "branch"
    main_ref.max_ref_age_ms = None
    main_ref.max_snapshot_age_ms = None
    main_ref.min_snapshots_to_keep = None

    tag_ref = MagicMock()
    tag_ref.snapshot_ref_type = "tag"

    mock_table = MagicMock()
    mock_table.metadata.refs = {"main": main_ref, "v1.0": tag_ref}
    mock_pyiceberg_catalog.load_table.return_value = mock_table

    result = client.list_branches("default", "orders")
    assert len(result) == 1
    assert result[0]["name"] == "main"
    assert result[0]["snapshot_id"] == 100


def test_list_tags(client, mock_pyiceberg_catalog):
    """Return only tag refs."""
    branch_ref = MagicMock()
    branch_ref.snapshot_ref_type = "branch"

    tag_ref = MagicMock()
    tag_ref.snapshot_id = 200
    tag_ref.snapshot_ref_type = "tag"
    tag_ref.max_ref_age_ms = None

    mock_table = MagicMock()
    mock_table.metadata.refs = {"main": branch_ref, "v1.0": tag_ref}
    mock_pyiceberg_catalog.load_table.return_value = mock_table

    result = client.list_tags("default", "orders")
    assert len(result) == 1
    assert result[0]["name"] == "v1.0"
    assert result[0]["snapshot_id"] == 200


def test_list_namespaces_not_found(client, mock_pyiceberg_catalog):
    """Raise NoSuchNamespaceError when catalog returns an error."""
    from pyiceberg.exceptions import NoSuchNamespaceError

    mock_pyiceberg_catalog.list_namespaces.side_effect = NoSuchNamespaceError("nope")
    with pytest.raises(NoSuchNamespaceError):
        client.list_namespaces()


def test_get_table_not_found(client, mock_pyiceberg_catalog):
    """Raise NoSuchTableError when table does not exist."""
    from pyiceberg.exceptions import NoSuchTableError

    mock_pyiceberg_catalog.load_table.side_effect = NoSuchTableError("nope")
    with pytest.raises(NoSuchTableError):
        client.get_table("default", "nonexistent")
