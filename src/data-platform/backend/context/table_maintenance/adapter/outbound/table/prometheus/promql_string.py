"""Define the promql_string function."""

from __future__ import annotations


def promql_string(value: str) -> str:
    """Return the double-quoted PromQL string literal of ``value``: backslash, quote and newline escaped."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'
