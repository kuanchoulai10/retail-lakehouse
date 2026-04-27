"""PyIceberg-based gateway implementing the ReadCatalogGateway port."""

from __future__ import annotations

from pyiceberg.catalog import load_catalog

from application.domain.model.catalog.branch import Branch
from application.domain.model.catalog.branch_id import BranchId
from application.domain.model.catalog.retention_policy import RetentionPolicy
from application.domain.model.catalog.schema_field import SchemaField
from application.domain.model.catalog.snapshot import Snapshot
from application.domain.model.catalog.snapshot_summary import SnapshotSummary
from application.domain.model.catalog.table import Table
from application.domain.model.catalog.table_id import TableId
from application.domain.model.catalog.table_schema import TableSchema
from application.domain.model.catalog.tag import Tag
from application.port.outbound.catalog.read_catalog.gateway import ReadCatalogGateway


class ReadCatalogIcebergGateway(ReadCatalogGateway):
    """Implement ReadCatalogGateway via PyIceberg REST catalog."""

    def __init__(
        self,
        catalog_uri: str,
        catalog_name: str,
        credential: str = "",
        warehouse: str = "",
        scope: str = "",
    ) -> None:
        """Initialize with catalog connection parameters."""
        kwargs: dict[str, str] = {
            "name": catalog_name,
            "type": "rest",
            "uri": catalog_uri,
        }
        if credential:
            kwargs["credential"] = credential
        if warehouse:
            kwargs["warehouse"] = warehouse
        if scope:
            kwargs["scope"] = scope
        self._catalog = load_catalog(**kwargs)

    def list_namespaces(self) -> list[str]:
        """Return namespace names as a flat list of strings."""
        raw = self._catalog.list_namespaces()
        return [ns[0] for ns in raw]

    def list_tables(self, namespace: str) -> list[str]:
        """Return table names within a namespace."""
        raw = self._catalog.list_tables(namespace=namespace)
        return [tbl[-1] for tbl in raw]

    def load_table(self, namespace: str, table: str) -> Table:
        """Load the full Table aggregate from PyIceberg."""
        tbl = self._catalog.load_table(f"{namespace}.{table}")
        return Table(
            id=TableId(value=f"{namespace}.{table}"),
            namespace=namespace,
            name=table,
            location=tbl.metadata.location,
            current_snapshot_id=tbl.metadata.current_snapshot_id,
            schema=TableSchema(
                fields=tuple(
                    SchemaField(
                        field_id=f.field_id,
                        name=f.name,
                        field_type=str(f.field_type),
                        required=f.required,
                    )
                    for f in tbl.schema().fields
                ),
            ),
            snapshots=tuple(
                Snapshot(
                    snapshot_id=snap.snapshot_id,
                    parent_id=snap.parent_snapshot_id,
                    timestamp_ms=snap.timestamp_ms,
                    summary=SnapshotSummary(
                        data=snap.summary.model_dump() if snap.summary else {},
                    ),
                )
                for snap in tbl.metadata.snapshots
            ),
            branches=tuple(
                Branch(
                    id=BranchId(value=name),
                    snapshot_id=ref.snapshot_id,
                    retention=RetentionPolicy(
                        max_snapshot_age_ms=ref.max_snapshot_age_ms,
                        max_ref_age_ms=ref.max_ref_age_ms,
                        min_snapshots_to_keep=ref.min_snapshots_to_keep,
                    ),
                )
                for name, ref in tbl.metadata.refs.items()
                if ref.snapshot_ref_type == "branch"
            ),
            tags=tuple(
                Tag(
                    name=name,
                    snapshot_id=ref.snapshot_id,
                    max_ref_age_ms=ref.max_ref_age_ms,
                )
                for name, ref in tbl.metadata.refs.items()
                if ref.snapshot_ref_type == "tag"
            ),
            properties=dict(tbl.metadata.properties),
        )
