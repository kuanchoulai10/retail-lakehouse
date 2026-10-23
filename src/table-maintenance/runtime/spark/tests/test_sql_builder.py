from __future__ import annotations

import re

import pytest

from sql_builder import build_call_statements, sql_literal
from tests.spark_rules import unescape_literal


def _where_literal(statement: str) -> str:
    match = re.search(r"where => ('(?:[^'\\]|\\.)*')", statement)
    assert match
    return match.group(1)


def test_call_per_filter_with_escaped_where(make_request):
    filters = ["region = 'o\\'neil'", "region = 'b'"]
    statements = build_call_statements(make_request(where=filters))
    assert len(statements) == 2
    assert [unescape_literal(_where_literal(s)) for s in statements] == filters
    assert statements[1].startswith(
        "CALL `iceberg`.system.rewrite_data_files(table => '`iceberg`.`sales`.`eu`.`orders`'"
    )


@pytest.mark.parametrize("text", ["a'b", "a\\b", "a\\'b", "trailing\\", "'", "\\\\'"])
def test_literal_round_trips(text):
    assert unescape_literal(sql_literal(text)) == text


@pytest.mark.parametrize("text", ["a'b", "a\\b", "a\\'b", "trailing\\"])
def test_where_round_trips(make_request, text):
    (statement,) = build_call_statements(make_request(where=[text]))
    assert unescape_literal(_where_literal(statement)) == text


def test_whole_table_when_no_filters(make_request):
    for where in ([], [""]):
        (statement,) = build_call_statements(make_request(where=where))
        assert "where" not in statement


def test_rewrite_data_files_options(make_request):
    (statement,) = build_call_statements(make_request())
    assert (
        "options => map('target-file-size-bytes', '536870912', 'min-input-files', '2', "
        "'partial-progress.enabled', 'true')"
    ) in statement


def test_rewrite_manifests_only_table(make_request):
    (statement,) = build_call_statements(make_request(operation="rewrite_manifests", procedure_args={}))
    assert statement == ("CALL `iceberg`.system.rewrite_manifests(table => '`iceberg`.`sales`.`eu`.`orders`')")


def test_expire_snapshots_args(make_request):
    (statement,) = build_call_statements(
        make_request(
            operation="expire_snapshots",
            procedure_args={"older_than": "2026-10-23T12:00:00+00:00", "retain_last": 10},
        )
    )
    assert "older_than => TIMESTAMP '2026-10-23 12:00:00'" in statement
    assert "retain_last => 10" in statement


def test_remove_orphan_files_args(make_request):
    (statement,) = build_call_statements(
        make_request(
            operation="remove_orphan_files",
            procedure_args={"older_than": "2026-10-21T12:00:00+00:00"},
        )
    )
    assert statement.endswith("older_than => TIMESTAMP '2026-10-21 12:00:00', prefix_listing => true)")


def test_remove_orphan_files_lists_through_file_io(make_request):
    """S3FileIO lists the table location; Hadoop has no FileSystem for the s3 scheme."""
    (statement,) = build_call_statements(
        make_request(
            operation="remove_orphan_files",
            procedure_args={"older_than": "2026-10-21T12:00:00+00:00"},
        )
    )
    assert "prefix_listing => true" in statement


def test_backtick_in_identifier_is_doubled(make_request):
    (statement,) = build_call_statements(make_request(namespace="a`b", table="t"))
    assert "table => '`iceberg`.`a``b`.`t`'" in statement


def test_unknown_operation_rejected(make_request):
    with pytest.raises(ValueError, match="Unsupported"):
        build_call_statements(make_request(operation="drop_table"))
