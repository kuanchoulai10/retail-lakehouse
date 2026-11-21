"""Public API of context.table_maintenance.application.domain.service.table_discovery_policy_attachment."""

from __future__ import annotations

from context.table_maintenance.application.domain.service.table_discovery_policy_attachment.decide_table_discovery import (  # noqa: E501
    decide_table_discovery,
)
from context.table_maintenance.application.domain.service.table_discovery_policy_attachment.scanned_catalogs import (  # noqa: E501
    scanned_catalogs,
)

__all__ = [
    "decide_table_discovery",
    "scanned_catalogs",
]
