"""Define the CreateTableUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class CreateTableUseCaseInput(UseCaseInput):
    """Carry the create table form: name, schema fields, optional partition fields, optional location, properties.

    Columns get ids 1, 2, ... in form order. With no partition fields the table is
    unpartitioned; with no location the catalog picks one under the namespace.
    """

    class SchemaField(UseCaseInput):
        """One column of the form: its name, its type as text, whether it is required, and its comment.

        ``type`` is an Iceberg primitive (``long``, ``decimal(10,2)``, ``fixed[16]``) or a nested
        type, ``struct<name: type, ...>``, ``list<type>`` or ``map<key, value>``, where a nested
        field or element that is required carries ``required`` before its type.
        """

        name: str
        type: str
        required: bool = True
        doc: str | None = None

    class PartitionField(UseCaseInput):
        """One partition field of the form: the top-level column it reads and its transform.

        ``transform`` is ``identity``, ``year``, ``month``, ``day``, ``hour``, ``void``,
        ``bucket[N]`` or ``truncate[W]``.
        """

        source_column: str
        transform: str

    catalog: str
    namespace: tuple[str, ...]
    name: str
    schema_fields: tuple[SchemaField, ...]
    partition_fields: tuple[PartitionField, ...] = ()
    location: str | None = None
    properties: dict[str, str] = {}
