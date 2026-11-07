"""Outbound ports for the view group."""

from __future__ import annotations

from context.catalog.application.domain.model.namespace import NamespaceId
from context.catalog.application.domain.model.view import View, ViewId, ViewVersion
from context.catalog.application.port.outbound.shared import Schema, SchemaField
from context.catalog.application.port.outbound.view.views_repo import ViewsRepo

__all__ = [
    "NamespaceId",
    "Schema",
    "SchemaField",
    "View",
    "ViewId",
    "ViewVersion",
    "ViewsRepo",
]
