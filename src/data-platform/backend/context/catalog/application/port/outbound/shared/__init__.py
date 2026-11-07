"""Outbound port vocabulary shared by several aggregates: an Iceberg schema and its fields."""

from __future__ import annotations

from context.catalog.application.domain.model.shared import Schema, SchemaField

__all__ = ["Schema", "SchemaField"]
