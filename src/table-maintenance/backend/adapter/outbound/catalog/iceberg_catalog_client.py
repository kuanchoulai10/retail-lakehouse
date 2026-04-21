"""PyIceberg-based catalog client for reading Iceberg metadata."""

from __future__ import annotations

from pyiceberg.catalog import load_catalog


class IcebergCatalogClient:
    """Wrap PyIceberg catalog operations, returning plain dicts."""

    def __init__(
        self,
        catalog_uri: str,
        catalog_name: str,
        credential: str = "",
        warehouse: str = "",
        scope: str = "",
    ) -> None:
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

    def get_table(self, namespace: str, table: str) -> dict:
        """Return table metadata as a plain dict."""
        tbl = self._catalog.load_table(f"{namespace}.{table}")
        schema_fields = [
            {
                "id": f.field_id,
                "name": f.name,
                "type": str(f.field_type),
                "required": f.required,
            }
            for f in tbl.schema().fields
        ]
        return {
            "table": table,
            "namespace": namespace,
            "location": tbl.metadata.location,
            "current_snapshot_id": tbl.metadata.current_snapshot_id,
            "schema": {"fields": schema_fields},
            "properties": dict(tbl.metadata.properties),
        }

    def list_snapshots(self, namespace: str, table: str) -> list[dict]:
        """Return snapshots as a list of plain dicts."""
        tbl = self._catalog.load_table(f"{namespace}.{table}")
        return [
            {
                "snapshot_id": snap.snapshot_id,
                "parent_id": snap.parent_snapshot_id,
                "timestamp_ms": snap.timestamp_ms,
                "summary": {k: v for k, v in snap.summary.items()}
                if snap.summary
                else {},
            }
            for snap in tbl.metadata.snapshots
        ]

    def list_branches(self, namespace: str, table: str) -> list[dict]:
        """Return branch refs as a list of plain dicts."""
        tbl = self._catalog.load_table(f"{namespace}.{table}")
        return [
            {
                "name": name,
                "snapshot_id": ref.snapshot_id,
                "max_snapshot_age_ms": ref.max_snapshot_age_ms,
                "max_ref_age_ms": ref.max_ref_age_ms,
                "min_snapshots_to_keep": ref.min_snapshots_to_keep,
            }
            for name, ref in tbl.metadata.refs.items()
            if ref.snapshot_ref_type == "branch"
        ]

    def list_tags(self, namespace: str, table: str) -> list[dict]:
        """Return tag refs as a list of plain dicts."""
        tbl = self._catalog.load_table(f"{namespace}.{table}")
        return [
            {
                "name": name,
                "snapshot_id": ref.snapshot_id,
                "max_ref_age_ms": ref.max_ref_age_ms,
            }
            for name, ref in tbl.metadata.refs.items()
            if ref.snapshot_ref_type == "tag"
        ]
