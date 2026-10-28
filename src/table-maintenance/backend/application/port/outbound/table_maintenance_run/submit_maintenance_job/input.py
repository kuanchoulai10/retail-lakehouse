"""Define the SubmitMaintenanceJobGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


@dataclass(frozen=True)
class SubmitMaintenanceJobGatewayInput:
    """Carry the arguments to submit a maintenance job to Spark."""

    run_id: str
    operation: str
    attempt: int
    catalog: str
    namespace: str
    table: str
    where: list[str]
    procedure_args: dict[str, Any]
    callback_url: str
