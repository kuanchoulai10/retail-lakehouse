"""Web adapter pieces shared by every aggregate router: the use case bundle and its dependency."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.shared.use_cases_dependency import (
    use_cases_dependency,
)
from context.table_maintenance.adapter.inbound.web.shared.web_use_cases import (
    WebUseCases,
)

__all__ = [
    "WebUseCases",
    "use_cases_dependency",
]
