"""Tests for the WakeReason enum."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_reconciliation import WakeReason


def test_wake_reason_values():
    """A reconciliation wakes for a schedule, a catalog or discovery event, a policy change, a request or a grant."""
    assert [r.value for r in WakeReason] == [
        "schedule",
        "catalog_commit",
        "discovery_scan",
        "policy_changed",
        "manual_run",
        "reconcile_now",
        "previous_run_finished",
        "compaction_granted",
    ]
