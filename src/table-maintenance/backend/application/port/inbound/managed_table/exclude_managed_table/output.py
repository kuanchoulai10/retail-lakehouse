"""Define the ExcludeManagedTableUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


@dataclass(frozen=True)
class ExcludeManagedTableUseCaseOutput:
    """Describe the managed table after the operation."""

    uuid: str
    catalog: str
    namespace: str
    table: str
    status: str
    selection: str
    settings: dict[str, Any] | None
    matched_rule_id: str | None
    source_template_id: str | None
    operation_states: dict[str, dict[str, Any]]
    registered_at: datetime
    updated_at: datetime
