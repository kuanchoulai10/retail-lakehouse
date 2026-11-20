"""Define the render_table_metrics_exposition function."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from context.table_maintenance.application.port.inbound.table import ListTableMetricsUseCaseOutput

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

_FILE_CONTENTS: tuple[tuple[str, str], ...] = (
    ("data", "data_files"),
    ("position_delete", "position_delete_files"),
    ("equality_delete", "equality_delete_files"),
    ("deletion_vector", "deletion_vectors"),
)
_SINGLE_VALUE_FAMILIES: tuple[tuple[str, str, str], ...] = (
    ("iceberg_table_data_size_bytes", "Bytes of the table's data files.", "data_size_bytes"),
    ("iceberg_table_data_records", "Records in the table's data files.", "data_records"),
    (
        "iceberg_table_position_delete_records",
        "Records in the table's position delete files and deletion vectors.",
        "position_delete_records",
    ),
    (
        "iceberg_table_equality_delete_records",
        "Records in the table's equality delete files.",
        "equality_delete_records",
    ),
    ("iceberg_table_reducible_files", "Files a compaction of the whole table would remove.", "reducible_files"),
    ("iceberg_table_manifests", "Manifests of the table's current snapshot.", "manifests"),
    ("iceberg_table_manifests_size_bytes", "Bytes of the manifests of the current snapshot.", "manifests_size_bytes"),
    ("iceberg_table_snapshots", "Snapshots the table holds.", "snapshots"),
)
_ENTRY_STATUSES: tuple[tuple[str, str], ...] = (
    ("added", "manifest_added_entries"),
    ("existing", "manifest_existing_entries"),
    ("deleted", "manifest_deleted_entries"),
)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _labels(**labels: str) -> str:
    return ",".join(f'{name}="{_escape(value)}"' for name, value in labels.items())


def _seconds(moment: datetime) -> str:
    milliseconds = (moment - _EPOCH) // timedelta(milliseconds=1)
    whole, fraction = divmod(milliseconds, 1000)
    return f"{whole}.{fraction:03d}".rstrip("0").rstrip(".")


def _family(name: str, help_text: str, samples: Iterator[str]) -> list[str]:
    return [f"# HELP {name} {help_text}", f"# TYPE {name} gauge", *samples]


def render_table_metrics_exposition(output: ListTableMetricsUseCaseOutput) -> str:
    """Render the tables' metrics as Prometheus text: gauges only, no timestamps, one sample per series."""
    tables = output.tables

    def per_table(name: str, value: Callable[[ListTableMetricsUseCaseOutput.Table], str]) -> Iterator[str]:
        return (f"{name}{{{_labels(table_uuid=t.table_uuid)}}} {value(t)}" for t in tables)

    lines: list[str] = []
    lines += _family(
        "iceberg_table_info",
        "Names of a managed table; the value is always 1.",
        (
            "iceberg_table_info{"
            + _labels(table_uuid=t.table_uuid, catalog=t.catalog, namespace=t.namespace, table=t.table)
            + "} 1"
            for t in tables
        ),
    )
    lines += _family(
        "iceberg_table_observed_timestamp_seconds",
        "Unix time in seconds when a reconcile observed the table.",
        per_table("iceberg_table_observed_timestamp_seconds", lambda t: _seconds(t.observed_at)),
    )
    lines += _family(
        "iceberg_table_files",
        "Live files of the table by content; the sum over content is every live file.",
        (
            f"iceberg_table_files{{{_labels(table_uuid=t.table_uuid, content=content)}}} {t.counts[field]}"
            for t in tables
            for content, field in _FILE_CONTENTS
        ),
    )
    for name, help_text, field in _SINGLE_VALUE_FAMILIES:
        lines += _family(name, help_text, per_table(name, lambda t, f=field: str(t.counts[f])))
    lines += _family(
        "iceberg_table_manifest_entries",
        "Entries of the current snapshot's manifests by status.",
        (
            f"iceberg_table_manifest_entries{{{_labels(table_uuid=t.table_uuid, status=status)}}} {t.counts[field]}"
            for t in tables
            for status, field in _ENTRY_STATUSES
        ),
    )
    return "\n".join(lines) + "\n"
