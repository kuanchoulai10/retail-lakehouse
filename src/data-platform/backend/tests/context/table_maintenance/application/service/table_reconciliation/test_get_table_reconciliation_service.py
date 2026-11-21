"""Test the GetTableReconciliationService."""

from __future__ import annotations

import pytest

from base import InvariantViolation
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    GetTableReconciliationUseCaseInput,
    ListTableReconciliationsUseCaseInput,
)
from context.table_maintenance.application.service.table_reconciliation import (
    GetTableReconciliationService,
    ListTableReconciliationsService,
    RecordTableReconciliationService,
)
from tests.context.table_maintenance.application.service.table_reconciliation.test_record_table_reconciliation_service import (  # noqa: E501
    _input,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policies_repo import (
    InMemoryTableMaintenancePoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_reconciliations_repo import (
    InMemoryTableReconciliationsRepo,
)

REC_1 = "rc-00000000000000000000000001"
UNKNOWN = "rc-00000000000000000000000009"


def test_get_reconciliation_by_id() -> None:
    """A recorded reconciliation reads by id with the fields the listing shows for it."""
    repo, policies = InMemoryTableReconciliationsRepo(), InMemoryTableMaintenancePoliciesRepo()
    RecordTableReconciliationService(repo).execute(_input())

    got = GetTableReconciliationService(repo, policies).execute(
        GetTableReconciliationUseCaseInput(reconciliation_id=REC_1)
    )

    (listed,) = (
        ListTableReconciliationsService(repo, policies)
        .execute(ListTableReconciliationsUseCaseInput(table_uuid="table-1"))
        .items
    )
    assert got.model_dump() == listed.model_dump()
    assert got.operations[0].run_id == "mr-00000000000000000000000001"


def test_get_unknown_reconciliation_is_not_found() -> None:
    """An id nothing was recorded under is NotFoundError."""
    service = GetTableReconciliationService(InMemoryTableReconciliationsRepo(), InMemoryTableMaintenancePoliciesRepo())

    with pytest.raises(NotFoundError):
        service.execute(GetTableReconciliationUseCaseInput(reconciliation_id=UNKNOWN))


def test_get_a_malformed_id_is_a_client_error() -> None:
    """An id that is not an rc- id is refused as invalid, not looked up."""
    service = GetTableReconciliationService(InMemoryTableReconciliationsRepo(), InMemoryTableMaintenancePoliciesRepo())

    with pytest.raises(InvariantViolation):
        service.execute(GetTableReconciliationUseCaseInput(reconciliation_id="not-an-id"))
