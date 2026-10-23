"""Build Iceberg system procedure CALL statements from a JobRequest."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

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


def _extra_args(request: JobRequest) -> list[str]:
    args = request.procedure_args
    match request.operation:
        case "rewrite_data_files":
            pairs = ", ".join(f"{sql_literal(k)}, {sql_literal(_option_text(v))}" for k, v in args.items())
            return [f"options => map({pairs})"] if pairs else []
        case "expire_snapshots":
            return [
                f"older_than => {_timestamp(args['older_than'])}",
                f"retain_last => {int(args['retain_last'])}",
            ]
        case "remove_orphan_files":
            return [f"older_than => {_timestamp(args['older_than'])}", "prefix_listing => true"]
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
