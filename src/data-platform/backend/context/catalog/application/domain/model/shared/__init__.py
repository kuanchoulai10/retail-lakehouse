"""Domain vocabulary shared by several aggregates: an Iceberg schema, its fields, their kinds, the id separator rule."""

from __future__ import annotations

from context.catalog.application.domain.model.shared.reject_unit_separator import (
    reject_unit_separator,
)
from context.catalog.application.domain.model.shared.schema import Schema
from context.catalog.application.domain.model.shared.schema_field import SchemaField
from context.catalog.application.domain.model.shared.schema_field_at_path import SchemaFieldAtPath
from context.catalog.application.domain.model.shared.schema_field_kind import SchemaFieldKind

__all__ = ["Schema", "SchemaField", "SchemaFieldAtPath", "SchemaFieldKind", "reject_unit_separator"]
