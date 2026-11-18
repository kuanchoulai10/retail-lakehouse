"""Define the CreateViewUseCaseOutput."""

from __future__ import annotations

from typing import Any

from base import UseCaseOutput


class CreateViewUseCaseOutput(UseCaseOutput):
    """Describe the view as the catalog saved it, every field primitive.

    ``query`` (the SQL text), ``dialect`` and ``default_namespace`` are the current version's. ``schema`` is
    ``{schema_id, fields: [{id, name, type, required, doc}]}`` with ``type`` as text;
    ``versions`` is ``[{version_id, timestamp_ms, query}]``, oldest first as the catalog lists them.
    """

    catalog: str
    namespace: tuple[str, ...]
    name: str
    uuid: str
    location: str
    query: str
    dialect: str
    default_namespace: tuple[str, ...]
    current_version_id: int
    schema: dict[str, Any]
    versions: tuple[dict[str, Any], ...]
    properties: dict[str, str]
