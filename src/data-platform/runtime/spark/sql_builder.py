"""Build Iceberg system procedure CALL statements from a JobRequest."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from job_request import OPERATIONS

if TYPE_CHECKING:
    from job_request import JobRequest


def sql_literal(value: str) -> str:
    """Return a Spark SQL single-quoted string literal.

    Spark treats backslash as an escape, and a doubled quote concatenates two literals,
    so backslashes are doubled first and quotes are backslash-escaped second.
    """
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def _quote_identifier(part: str) -> str:
    return "`" + part.replace("`", "``") + "`"


def _table_literal(request: JobRequest) -> str:
    parts = [request.catalog, *request.namespace.split("."), request.table]
    return sql_literal(".".join(_quote_identifier(p) for p in parts))


def _timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return f"TIMESTAMP '{parsed.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}'"


def _option_text(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


_STRATEGIES = ("binpack", "sort")
_PREFIX_MISMATCH_MODES = ("ERROR", "IGNORE", "DELETE")


def _refuse_unknown(operation: str, args: dict[str, Any], known: tuple[str, ...]) -> None:
    unknown = sorted(set(args) - set(known))
    if unknown:
        raise ValueError(f"Unsupported {operation} argument: {', '.join(unknown)}")


def _bool_arg(name: str, value: object) -> str:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean, got {value!r}")
    return "true" if value else "false"


def _positive_int_arg(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")
    return value


def _choice_arg(name: str, value: object, choices: tuple[str, ...]) -> str:
    if value not in choices:
        raise ValueError(f"{name} must be one of {', '.join(choices)}, got {value!r}")
    return str(value)


def _string_arg(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string, got {value!r}")
    return value


def _rewrite_data_files_args(args: dict[str, Any]) -> list[str]:
    _refuse_unknown("rewrite_data_files", args, ("strategy", "sort_order", "options"))
    rendered: list[str] = []
    if "strategy" in args:
        rendered.append(f"strategy => {sql_literal(_choice_arg('strategy', args['strategy'], _STRATEGIES))}")
    if "sort_order" in args:
        rendered.append(f"sort_order => {sql_literal(_string_arg('sort_order', args['sort_order']))}")
    options = args.get("options") or {}
    if not isinstance(options, dict):
        raise ValueError(f"options must be an object, got {options!r}")
    if options:
        pairs = ", ".join(f"{sql_literal(k)}, {sql_literal(_option_text(v))}" for k, v in options.items())
        rendered.append(f"options => map({pairs})")
    return rendered


def _rewrite_manifests_args(args: dict[str, Any]) -> list[str]:
    _refuse_unknown("rewrite_manifests", args, ("use_caching",))
    return [f"use_caching => {_bool_arg('use_caching', args['use_caching'])}"] if "use_caching" in args else []


def _expire_snapshots_args(args: dict[str, Any]) -> list[str]:
    _refuse_unknown("expire_snapshots", args, ("older_than", "retain_last", "max_concurrent_deletes", "stream_results"))
    rendered = [
        f"older_than => {_timestamp(args['older_than'])}",
        f"retain_last => {_positive_int_arg('retain_last', args['retain_last'])}",
    ]
    if "max_concurrent_deletes" in args:
        rendered.append(
            f"max_concurrent_deletes => {_positive_int_arg('max_concurrent_deletes', args['max_concurrent_deletes'])}"
        )
    if "stream_results" in args:
        rendered.append(f"stream_results => {_bool_arg('stream_results', args['stream_results'])}")
    return rendered


def _remove_orphan_files_args(args: dict[str, Any]) -> list[str]:
    _refuse_unknown("remove_orphan_files", args, ("older_than", "max_concurrent_deletes", "prefix_mismatch_mode"))
    rendered = [f"older_than => {_timestamp(args['older_than'])}", "prefix_listing => true"]
    if "max_concurrent_deletes" in args:
        rendered.append(
            f"max_concurrent_deletes => {_positive_int_arg('max_concurrent_deletes', args['max_concurrent_deletes'])}"
        )
    if "prefix_mismatch_mode" in args:
        mode = _choice_arg("prefix_mismatch_mode", args["prefix_mismatch_mode"], _PREFIX_MISMATCH_MODES)
        rendered.append(f"prefix_mismatch_mode => {sql_literal(mode)}")
    return rendered


def _extra_args(request: JobRequest) -> list[str]:
    args = request.procedure_args
    match request.operation:
        case "rewrite_data_files":
            return _rewrite_data_files_args(args)
        case "rewrite_manifests":
            return _rewrite_manifests_args(args)
        case "expire_snapshots":
            return _expire_snapshots_args(args)
        case "remove_orphan_files":
            return _remove_orphan_files_args(args)
        case _:
            return []


def build_call_statements(request: JobRequest) -> list[str]:
    """Return one CALL statement per filter, or one whole-table CALL."""
    if request.operation not in OPERATIONS:
        raise ValueError(f"Unsupported operation: {request.operation}")
    base = [f"table => {_table_literal(request)}", *_extra_args(request)]
    filters = [f for f in request.where if f]
    where_args = [[f"where => {sql_literal(f)}"] for f in filters] or [[]]
    catalog = _quote_identifier(request.catalog)
    return [f"CALL {catalog}.system.{request.operation}({', '.join([*base, *w])})" for w in where_args]
