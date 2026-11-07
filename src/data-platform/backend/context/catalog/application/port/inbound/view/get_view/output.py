"""Define the GetViewUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


@dataclass(frozen=True)
class GetViewUseCaseOutput:
    """Describe the view as the catalog holds it, every field primitive.

    ``query`` (the SQL text), ``dialect`` and ``default_namespace`` are the current version's. ``schema`` is
    ``{schema_id, fields: [{id, name, type, required, doc}]}`` with ``type`` as text;
    ``versions`` is ``[{version_id, timestamp_ms, query}]``, oldest first as the catalog lists them.
    """

    catalog: str
    namespace: list[str]
    name: str
    uuid: str
    location: str
    query: str
    dialect: str
    default_namespace: list[str]
    current_version_id: int
    schema: dict[str, Any]
    versions: list[dict[str, Any]]
    properties: dict[str, str]
