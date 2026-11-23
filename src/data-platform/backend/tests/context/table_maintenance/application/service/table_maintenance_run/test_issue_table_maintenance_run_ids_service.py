"""Test IssueTableMaintenanceRunIdsService: the application issues the ids of a plan's runs."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import TableMaintenanceRunId
from context.table_maintenance.application.exceptions import ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    IssueTableMaintenanceRunIdsUseCaseInput,
)
from context.table_maintenance.application.service.table_maintenance_run import IssueTableMaintenanceRunIdsService


@pytest.mark.parametrize("count", [0, 1, 4])
def test_it_issues_as_many_distinct_run_ids_as_asked(count):
    """The output holds ``count`` distinct ``mr-`` ids, which the run id type accepts."""
    run_ids = IssueTableMaintenanceRunIdsService().execute(IssueTableMaintenanceRunIdsUseCaseInput(count=count)).run_ids

    assert len(run_ids) == count
    assert len(set(run_ids)) == count
    assert all(TableMaintenanceRunId(run_id).value.startswith("mr-") for run_id in run_ids)


def test_a_negative_count_is_refused():
    """A negative count is a malformed request, refused as a validation error."""
    with pytest.raises(ValidationError, match="count must be at least 0, got -1"):
        IssueTableMaintenanceRunIdsService().execute(IssueTableMaintenanceRunIdsUseCaseInput(count=-1))
