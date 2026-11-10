"""Define the View aggregate root."""

from __future__ import annotations

from pydantic import Field

from base.model import AggregateRoot
from context.catalog.application.domain.model.shared import Schema
from context.catalog.application.domain.model.view.view_id import ViewId
from context.catalog.application.domain.model.view.view_version import ViewVersion

_FIRST_VERSION = 1
_NO_SCHEMA_ID = 0


class View(AggregateRoot[ViewId]):
    """An Iceberg view as the catalog holds it: uuid, location, schema, versions and properties.

    ``current_schema`` is the schema of the current version, the same shape as a table's. The catalog
    assigns ``uuid`` and, unless one is asked for, ``location`` when it saves the view; a view
    defined for create (``define``) has them as None, every view loaded from the catalog has them.
    """

    id: ViewId
    uuid: str | None
    location: str | None
    current_schema: Schema
    current_version_id: int
    versions: list[ViewVersion] = Field(default_factory=list)
    properties: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def define(
        cls,
        id: ViewId,  # noqa: A002
        query: str,
        dialect: str,
        default_namespace: tuple[str, ...],
        timestamp_ms: int,
    ) -> View:
        """Return a new view with one version holding ``query`` and an empty schema, for the catalog to create."""
        return cls(
            id=id,
            uuid=None,
            location=None,
            current_schema=Schema(schema_id=_NO_SCHEMA_ID, fields=()),
            current_version_id=_FIRST_VERSION,
            versions=[
                ViewVersion(
                    version_id=_FIRST_VERSION,
                    timestamp_ms=timestamp_ms,
                    schema_id=_NO_SCHEMA_ID,
                    query=query,
                    dialect=dialect,
                    default_namespace=default_namespace,
                )
            ],
            properties={},
        )

    @property
    def current_version(self) -> ViewVersion:
        """Return the version the view points at; ValueError when no version has that id."""
        for version in self.versions:
            if version.version_id == self.current_version_id:
                return version
        raise ValueError(f"current version {self.current_version_id} matches no version")

    @property
    def query(self) -> str:
        """Return the query (the SQL text) of the current version."""
        return self.current_version.query

    @property
    def dialect(self) -> str:
        """Return the sql dialect of the current version."""
        return self.current_version.dialect

    @property
    def default_namespace(self) -> tuple[str, ...]:
        """Return the namespace the current version's query resolves unqualified names in."""
        return self.current_version.default_namespace
