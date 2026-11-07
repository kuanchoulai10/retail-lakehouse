"""View domain vocabulary: the Iceberg view aggregate, its id and its versions."""

from __future__ import annotations

from context.catalog.application.domain.model.view.view import View
from context.catalog.application.domain.model.view.view_id import ViewId
from context.catalog.application.domain.model.view.view_version import ViewVersion

__all__ = ["View", "ViewId", "ViewVersion"]
