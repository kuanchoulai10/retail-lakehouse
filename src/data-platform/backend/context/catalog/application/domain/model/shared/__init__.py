"""Domain vocabulary shared by several aggregates: an Iceberg schema and its fields."""

from __future__ import annotations

from context.catalog.application.domain.model.shared.schema import Schema
from context.catalog.application.domain.model.shared.schema_field import SchemaField

__all__ = ["Schema", "SchemaField"]
