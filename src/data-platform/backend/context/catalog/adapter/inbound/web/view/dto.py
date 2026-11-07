"""Define the view API DTOs.

Schema field types are text in the syntax described in the table API DTOs. Version ids are
small integers, so they stay numbers.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from context.catalog.adapter.inbound.web.shared import SchemaApiResponse


class CreateViewApiRequest(BaseModel):
    """Carry the create view form: name, sql and the sql dialect."""

    model_config = ConfigDict(extra="forbid")

    name: str
    sql: str
    dialect: str


class ViewVersionApiResponse(BaseModel):
    """One version of the view: its id, when it was made and its sql, which the JSON names ``sql``."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    version_id: int
    timestamp_ms: int
    query: str = Field(serialization_alias="sql")


class ViewApiResponse(BaseModel):
    """Describe an Iceberg view: what the view page's sql, schema, versions and properties show.

    ``sql`` (the application's ``query``), ``dialect`` and ``default_namespace`` are the current version's, and
    ``view_schema`` (``schema`` in JSON) is the schema of that version.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    catalog: str
    namespace: list[str]
    name: str
    uuid: str
    location: str
    query: str = Field(serialization_alias="sql")
    dialect: str
    default_namespace: list[str]
    current_version_id: int
    view_schema: SchemaApiResponse = Field(alias="schema")
    versions: list[ViewVersionApiResponse]
    properties: dict[str, str]


class ViewIdentifierApiResponse(BaseModel):
    """Name a view in a listing."""

    model_config = ConfigDict(from_attributes=True)

    catalog: str
    namespace: list[str]
    name: str
