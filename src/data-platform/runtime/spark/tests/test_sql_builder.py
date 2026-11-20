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


def test_rewrite_data_files_renders_strategy_sort_order_and_options(make_request):
    (statement,) = build_call_statements(
        make_request(
            procedure_args={
                "strategy": "sort",
                "sort_order": "id DESC NULLS LAST",
                "options": {"target-file-size-bytes": 536870912, "min-input-files": 2},
            }
        )
    )
    assert (
        "table => '`iceberg`.`sales`.`eu`.`orders`', strategy => 'sort', sort_order => 'id DESC NULLS LAST', "
        "options => map('target-file-size-bytes', '536870912', 'min-input-files', '2')"
    ) in statement


def test_rewrite_data_files_renders_boolean_options_in_lower_case(make_request):
    (statement,) = build_call_statements(
        make_request(procedure_args={"options": {"rewrite-all": True, "remove-dangling-deletes": False}})
    )
    assert "options => map('rewrite-all', 'true', 'remove-dangling-deletes', 'false')" in statement


def test_rewrite_data_files_leaves_out_an_empty_options_map(make_request):
    (statement,) = build_call_statements(make_request(procedure_args={"strategy": "binpack", "options": {}}))
    assert statement.endswith("strategy => 'binpack')")


def test_a_sort_order_cannot_break_out_of_its_literal(make_request):
    sort_order = "id') ; DROP TABLE x; --\\"
    (statement,) = build_call_statements(
        make_request(procedure_args={"strategy": "sort", "sort_order": sort_order, "options": {}})
    )
    match = re.search(r"sort_order => ('(?:[^'\\]|\\.)*')", statement)
    assert match
    assert unescape_literal(match.group(1)) == sort_order
    assert statement.endswith(match.group(1) + ")")


def test_rewrite_manifests_renders_use_caching(make_request):
    (statement,) = build_call_statements(
        make_request(operation="rewrite_manifests", procedure_args={"use_caching": False})
    )
    assert statement == (
        "CALL `iceberg`.system.rewrite_manifests(table => '`iceberg`.`sales`.`eu`.`orders`', use_caching => false)"
    )


def test_expire_snapshots_renders_its_options(make_request):
    (statement,) = build_call_statements(
        make_request(
            operation="expire_snapshots",
            procedure_args={
                "older_than": "2026-10-23T12:00:00+00:00",
                "retain_last": 10,
                "max_concurrent_deletes": 4,
                "stream_results": True,
            },
        )
    )
    assert statement.endswith(
        "older_than => TIMESTAMP '2026-10-23 12:00:00', retain_last => 10, "
        "max_concurrent_deletes => 4, stream_results => true)"
    )


def test_remove_orphan_files_renders_prefix_mismatch_mode(make_request):
    (statement,) = build_call_statements(
        make_request(
            operation="remove_orphan_files",
            procedure_args={
                "older_than": "2026-10-21T12:00:00+00:00",
                "max_concurrent_deletes": 8,
                "prefix_mismatch_mode": "IGNORE",
            },
        )
    )
    assert statement.endswith(
        "older_than => TIMESTAMP '2026-10-21 12:00:00', prefix_listing => true, "
        "max_concurrent_deletes => 8, prefix_mismatch_mode => 'IGNORE')"
    )


def test_options_come_before_where(make_request):
    (statement,) = build_call_statements(
        make_request(operation="rewrite_manifests", procedure_args={"use_caching": True}, where=["a = 1"])
    )
    assert statement.endswith("use_caching => true, where => 'a = 1')")


def test_a_where_clause_still_makes_one_call_per_filter(make_request):
    statements = build_call_statements(make_request(where=["a = 1", "a = 2"], procedure_args={"strategy": "binpack"}))
    assert len(statements) == 2
    assert all("strategy => 'binpack'" in s for s in statements)
    assert statements[0].endswith("where => 'a = 1')")
    assert statements[1].endswith("where => 'a = 2')")


@pytest.mark.parametrize(
    ("operation", "args"),
    [
        ("expire_snapshots", {"retain_last": 1, "older_than": "2026-10-23T12:00:00+00:00", "foo": 1}),
        ("rewrite_manifests", {"use_caching": True, "foo": 1}),
        ("remove_orphan_files", {"older_than": "2026-10-21T12:00:00+00:00", "retain_last": 1}),
        ("rewrite_data_files", {"options": {}, "foo": 1}),
    ],
)
def test_an_unknown_argument_is_refused(make_request, operation, args):
    with pytest.raises(ValueError, match="foo|retain_last"):
        build_call_statements(make_request(operation=operation, procedure_args=args))


def test_a_flat_rewrite_option_is_refused(make_request):
    with pytest.raises(ValueError, match="min-input-files"):
        build_call_statements(make_request(procedure_args={"min-input-files": 2}))


def test_an_unknown_strategy_is_refused(make_request):
    with pytest.raises(ValueError, match="zorder"):
        build_call_statements(make_request(procedure_args={"strategy": "zorder", "options": {}}))


def test_an_unknown_prefix_mismatch_mode_is_refused(make_request):
    with pytest.raises(ValueError, match="prefix_mismatch_mode"):
        build_call_statements(
            make_request(
                operation="remove_orphan_files",
                procedure_args={"older_than": "2026-10-21T12:00:00+00:00", "prefix_mismatch_mode": "SKIP"},
            )
        )


@pytest.mark.parametrize(
    ("operation", "args"),
    [
        ("rewrite_manifests", {"use_caching": 1}),
        ("expire_snapshots", {"older_than": "2026-10-23T12:00:00+00:00", "retain_last": 1, "stream_results": "yes"}),
        ("expire_snapshots", {"older_than": "2026-10-23T12:00:00+00:00", "retain_last": True}),
        ("expire_snapshots", {"older_than": "2026-10-23T12:00:00+00:00", "retain_last": 0}),
        (
            "expire_snapshots",
            {"older_than": "2026-10-23T12:00:00+00:00", "retain_last": 1, "max_concurrent_deletes": 0},
        ),
        ("remove_orphan_files", {"older_than": "2026-10-21T12:00:00+00:00", "max_concurrent_deletes": -1}),
    ],
)
def test_a_wrongly_typed_or_non_positive_value_is_refused(make_request, operation, args):
    with pytest.raises(ValueError):
        build_call_statements(make_request(operation=operation, procedure_args=args))


@pytest.mark.parametrize("value", [1.5, None, ["a"], {"a": 1}])
def test_a_rewrite_option_of_another_type_is_refused(make_request, value):
    with pytest.raises(ValueError, match="min-input-files"):
        build_call_statements(make_request(procedure_args={"options": {"min-input-files": value}}))


@pytest.mark.parametrize(
    ("operation", "args", "key"),
    [
        ("expire_snapshots", {"retain_last": 1}, "older_than"),
        ("expire_snapshots", {"older_than": "2026-10-23T12:00:00+00:00"}, "retain_last"),
        ("remove_orphan_files", {}, "older_than"),
    ],
)
def test_a_missing_required_argument_is_refused(make_request, operation, args, key):
    with pytest.raises(ValueError, match=f"^{key} is required for {operation}$"):
        build_call_statements(make_request(operation=operation, procedure_args=args))
