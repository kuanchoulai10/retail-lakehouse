"""Test the Prometheus text exposition of the table metrics."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.adapter.inbound.web.table import render_table_metrics_exposition
from context.table_maintenance.application.domain.model.table import TABLE_METRIC_COUNT_FIELDS
from context.table_maintenance.application.port.inbound.table import ListTableMetricsUseCaseOutput

OBSERVED_AT = datetime(2026, 11, 20, 12, 0, 0, 123000, tzinfo=UTC)


def _output(
    uuid: str = "u1", table: str = "orders", namespace: str = "retail", **counts: int
) -> ListTableMetricsUseCaseOutput:
    return ListTableMetricsUseCaseOutput(
        tables=(
            ListTableMetricsUseCaseOutput.Table(
                table_uuid=uuid,
                catalog="iceberg",
                namespace=namespace,
                table=table,
                observed_at=OBSERVED_AT,
                counts={**dict.fromkeys(TABLE_METRIC_COUNT_FIELDS, 0), **counts},
            ),
        )
    )


def _samples(text: str) -> list[str]:
    return [line for line in text.splitlines() if line and not line.startswith("#")]


def test_exposition_of_one_table() -> None:
    """Each family is declared as a gauge and the table's samples carry its uuid."""
    text = render_table_metrics_exposition(_output(data_files=12, deletion_vectors=1, manifest_added_entries=4))

    assert "# TYPE iceberg_table_files gauge" in text
    assert 'iceberg_table_info{table_uuid="u1",catalog="iceberg",namespace="retail",table="orders"} 1\n' in text
    assert 'iceberg_table_files{table_uuid="u1",content="data"} 12\n' in text
    assert 'iceberg_table_files{table_uuid="u1",content="deletion_vector"} 1\n' in text
    assert 'iceberg_table_manifest_entries{table_uuid="u1",status="added"} 4\n' in text
    assert text.endswith("\n")


def test_observed_timestamp_is_seconds_with_milliseconds() -> None:
    """The observation time is epoch seconds with up to three decimals."""
    text = render_table_metrics_exposition(_output())

    assert 'iceberg_table_observed_timestamp_seconds{table_uuid="u1"} 1795176000.123\n' in text


def test_a_whole_second_has_no_decimals() -> None:
    """A whole second is written without a trailing decimal part."""
    output = _output()
    whole = output.model_copy(
        update={"tables": (output.tables[0].model_copy(update={"observed_at": datetime(2026, 11, 20, tzinfo=UTC)}),)}
    )

    text = render_table_metrics_exposition(whole)

    assert 'iceberg_table_observed_timestamp_seconds{table_uuid="u1"} 1795132800\n' in text


def test_label_values_are_escaped() -> None:
    """A backslash, a double quote and a newline in a label value are escaped."""
    text = render_table_metrics_exposition(_output(table='a"b\\c\nd'))

    assert 'table="a\\"b\\\\c\\nd"' in text
    assert all(line.startswith("iceberg_table_") for line in _samples(text))


def test_seventeen_samples_per_table() -> None:
    """One table yields 17 samples."""
    assert len(_samples(render_table_metrics_exposition(_output()))) == 17


def test_two_tables_share_one_declaration_per_family() -> None:
    """Two tables give 34 samples under the 12 families, each declared once by HELP and once by TYPE."""
    first, second = _output("u1", "orders"), _output("u2", "customers")
    text = render_table_metrics_exposition(ListTableMetricsUseCaseOutput(tables=first.tables + second.tables))
    lines = text.splitlines()

    assert sum(line.startswith("# HELP ") for line in lines) == 12
    assert sum(line.startswith("# TYPE ") for line in lines) == 12
    assert len(_samples(text)) == 34


def test_nothing_managed_leaves_only_the_declarations() -> None:
    """Without a table the text keeps every family's HELP and TYPE and has no sample."""
    text = render_table_metrics_exposition(ListTableMetricsUseCaseOutput(tables=()))

    assert _samples(text) == []
    assert "# HELP iceberg_table_info" in text
    assert "# TYPE iceberg_table_manifest_entries gauge" in text
    assert text.endswith("\n")


def test_families_follow_the_documented_order() -> None:
    """The families appear in the order info, observed timestamp, files, then the single-value ones."""
    text = render_table_metrics_exposition(_output())
    types = [line.split()[2] for line in text.splitlines() if line.startswith("# TYPE")]

    assert types == [
        "iceberg_table_info",
        "iceberg_table_observed_timestamp_seconds",
        "iceberg_table_files",
        "iceberg_table_data_size_bytes",
        "iceberg_table_data_records",
        "iceberg_table_position_delete_records",
        "iceberg_table_equality_delete_records",
        "iceberg_table_reducible_files",
        "iceberg_table_manifests",
        "iceberg_table_manifests_size_bytes",
        "iceberg_table_snapshots",
        "iceberg_table_manifest_entries",
    ]
