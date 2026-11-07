"""Define the CreateViewUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateViewUseCaseInput:
    """Carry the create view form: name, query (the SQL text) and the SQL dialect.

    The view is created with an empty schema and one version, whose default namespace is the
    namespace the view is created in.
    """

    catalog: str
    namespace: list[str]
    name: str
    query: str
    dialect: str
