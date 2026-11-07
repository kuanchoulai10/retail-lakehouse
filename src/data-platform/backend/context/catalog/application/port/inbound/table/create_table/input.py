"""Define the CreateTableUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CreateTableUseCaseInputSchemaField:
    """One column of the form: its name, its type as text, whether it is required, and its comment.

    ``type`` is an Iceberg primitive (``long``, ``decimal(10,2)``, ``fixed[16]``) or a nested
    type, ``struct<name: type, ...>``, ``list<type>`` or ``map<key, value>``, where a nested
    field or element that is required carries ``required`` before its type.
    """

    name: str
    type: str
    required: bool = True
    doc: str | None = None


@dataclass(frozen=True)
class CreateTableUseCaseInputPartitionField:
    """One partition field of the form: the top-level column it reads and its transform.

    ``transform`` is ``identity``, ``year``, ``month``, ``day``, ``hour``, ``void``,
    ``bucket[N]`` or ``truncate[W]``.
    """

    source_column: str
    transform: str


@dataclass(frozen=True)
class CreateTableUseCaseInput:
    """Carry the create table form: name, schema fields, optional partition fields, optional location, properties.

    Columns get ids 1, 2, ... in form order. With no partition fields the table is
    unpartitioned; with no location the catalog picks one under the namespace.
    """

    catalog: str
    namespace: list[str]
    name: str
    schema_fields: list[CreateTableUseCaseInputSchemaField]
    partition_fields: list[CreateTableUseCaseInputPartitionField] = field(default_factory=list)
    location: str | None = None
    properties: dict[str, str] = field(default_factory=dict)
