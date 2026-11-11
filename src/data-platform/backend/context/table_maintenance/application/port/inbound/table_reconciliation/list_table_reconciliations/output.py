"""Define the ListTableReconciliationsUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ListTableReconciliationsUseCaseOutputMeasurement:
    """One measurement of an operation; threshold, comparison and met are None for context."""

    key: str
    observed: int
    unit: str
    threshold: int | None
    comparison: str | None
    met: bool | None


@dataclass(frozen=True)
class ListTableReconciliationsUseCaseOutputOperation:
    """What a reconciliation measured and decided for one operation."""

    operation: str
    result: str
    measurements: list[ListTableReconciliationsUseCaseOutputMeasurement]
    next_eligible_at: datetime | None


@dataclass(frozen=True)
class ListTableReconciliationsUseCaseOutputPolicyTarget:
    """Where the policy a reconciliation used was attached."""

    type: str
    path: list[str]


@dataclass(frozen=True)
class ListTableReconciliationsUseCaseOutputItem:
    """One reconciliation of the listing."""

    reconciliation_id: str
    table_uuid: str
    reconciled_at: datetime
    wake_reasons: dict[str, int]
    dry_run: bool
    outcome: str
    skip_reason: str | None
    operations: list[ListTableReconciliationsUseCaseOutputOperation]
    run_id: str | None
    policy_name: str
    policy_version: int
    policy_target: ListTableReconciliationsUseCaseOutputPolicyTarget | None


@dataclass(frozen=True)
class ListTableReconciliationsUseCaseOutput:
    """Carry the result of the request to list the reconciliations of a table."""

    items: list[ListTableReconciliationsUseCaseOutputItem]
