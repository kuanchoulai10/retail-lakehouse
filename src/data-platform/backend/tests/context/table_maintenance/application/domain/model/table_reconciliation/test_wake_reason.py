"""Tests for the WakeReason enum."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_reconciliation import WakeReason


def test_wake_reason_values():
    """The wake reasons are the documented ones, in their documented order.

    A reconciliation wakes on its schedule, a catalog commit, a table becoming managed, a policy change,
    a request or a run's end.
    """
    assert [r.value for r in WakeReason] == [
        "schedule",
        "catalog_commit",
        "table_managed",
        "policy_changed",
        "manual_run",
        "reconcile_now",
        "previous_run_finished",
    ]
