"""Define the iceberg_type_from_polaris function."""

from __future__ import annotations

from typing import Any


def _required(flag: object) -> str:
    return "required " if flag else ""


def iceberg_type_from_polaris(iceberg_type: str | dict[str, Any]) -> str:
    """Render an Iceberg REST type as text: a primitive as its name, a nested type in the readable syntax.

    ``struct<name: type, ...>``, ``list<type>`` and ``map<key, value>``; a nested field, list
    element or map value that is required carries ``required`` before its type. Nested field
    ids and docs are not part of the text.
    """
    if isinstance(iceberg_type, str):
        return iceberg_type
    kind = iceberg_type.get("type")
    if kind == "struct":
        fields = ", ".join(
            f"{field['name']}: {_required(field.get('required'))}{iceberg_type_from_polaris(field['type'])}"
            for field in iceberg_type.get("fields", [])
        )
        return f"struct<{fields}>"
    if kind == "list":
        element = iceberg_type_from_polaris(iceberg_type["element"])
        return f"list<{_required(iceberg_type.get('element-required'))}{element}>"
    if kind == "map":
        key = iceberg_type_from_polaris(iceberg_type["key"])
        value = iceberg_type_from_polaris(iceberg_type["value"])
        return f"map<{key}, {_required(iceberg_type.get('value-required'))}{value}>"
    return str(kind)
