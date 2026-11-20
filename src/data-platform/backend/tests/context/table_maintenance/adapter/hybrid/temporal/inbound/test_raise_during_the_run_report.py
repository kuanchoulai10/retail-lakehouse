"""Test a manual run whose priority raise reaches the maintenance run while that run reports back.

The reconciliation and the real maintenance workflow run together on a time-skipping Temporal
test server, with scripted activities.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TableMaintenanceActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TABLE_RECONCILIATION_WORKFLOW,
    TableReconciliationSignal,
    TableReconciliationWorkflowInput,
    table_reconciliation_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
    TableMaintenanceWorkflow,
    TableReconciliationWorkflow,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.eventually import (
    eventually,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.register_table_search_attributes import (
    register_table_search_attributes,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.scripted_maintenance_activities import (
    ScriptedMaintenanceActivities,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.scripted_plan_activity import (
    ScriptedPlanActivity,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.scripted_record_activity import (
    ScriptedRecordActivity,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.table_maintenance_activities_with_fakes import (  # noqa: E501
    table_maintenance_activities_with_fakes,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.table_reconciliation_activities_with_fakes import (  # noqa: E501
    table_reconciliation_activities_with_fakes,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

UUID = "u1"
WORKFLOW_ID = table_reconciliation_workflow_id(UUID)
COMPACTION = "rewrite_data_files"
EXPIRE = "expire_snapshots"
REAL_TIMEOUT_SECONDS = 20


def _planned(request: dict[str, Any]) -> dict[str, Any]:
    """Plan the manual operations asked for, or a compaction."""
    operations = request["manual_operations"] or [COMPACTION]
    return {
        "status": "planned",
        "reason": None,
        "schedule_interval_seconds": 3600,
        "catalog_commit_debounce_seconds": 300,
        "table_name": "iceberg.e2e.t",
        "operations": [{"operation": op, "filters": [], "procedure_args": {}} for op in operations],
        "dry_run": False,
        "table_found": True,
        "checks": [],
        "policy_id": "mp-00000000000000000000000004",
        "policy_name": "nightly",
        "policy_version": 4,
        "policy_target": {"type": "catalog", "path": ["prod"]},
    }


def _run(scenario: Callable[[Any, ScriptedPlanActivity, list], Awaitable[None]]) -> None:
    """Run ``scenario`` with the reconciliation, the real maintenance workflow and a hookable report activity.

    The scenario gets the client, the plan activity and a list it may put one hook in: the first
    report a maintenance run sends its parent runs that hook before the report goes out.
    """

    async def go() -> None:
        async with await WorkflowEnvironment.start_time_skipping() as env:
            await register_table_search_attributes(env.client)
            plans = ScriptedPlanActivity(_planned)
            recorder = ScriptedRecordActivity()
            lookups = table_reconciliation_activities_with_fakes(client=env.client)
            maintenance = ScriptedMaintenanceActivities(env.client)
            maintenance.callbacks = {(COMPACTION, 1): [(1, True, None)], (EXPIRE, 1): [(1, True, None)]}
            signals = table_maintenance_activities_with_fakes(client=env.client)
            hooks: list[Callable[[], Awaitable[None]]] = []

            @activity.defn(name=TableMaintenanceActivity.SIGNAL_PARENT)
            async def signal_parent(request: dict[str, Any]) -> dict[str, bool]:
                if hooks:
                    await hooks.pop(0)()
                return await signals.signal_parent(request)

            async with Worker(
                env.client,
                task_queue=TASK_QUEUE,
                workflows=[TableReconciliationWorkflow, TableMaintenanceWorkflow],
                activities=[
                    plans.plan_table_maintenance,
                    recorder.record_table_reconciliation,
                    lookups.get_workflow_running,
                    *maintenance.all(),
                    signal_parent,
                ],
            ):
                await scenario(env.client, plans, hooks)

    asyncio.run(go())


def test_a_raise_delivered_while_the_run_reports_gives_the_manual_trigger_back():
    """A raise the run receives after it built its report is not lost: the manual run is planned after it.

    The run's report says it received no raise and left none unapplied; the reconciliation delivered
    one, so it gives the trigger back and plans the manual run with its operations and priority.
    """

    async def scenario(client: Any, plans: ScriptedPlanActivity, hooks: list) -> None:  # noqa: ANN401
        reconciliation = client.get_workflow_handle(WORKFLOW_ID)

        async def state() -> dict[str, Any]:
            return await reconciliation.query("state")

        async def raise_while_reporting() -> None:
            await reconciliation.signal(
                TableReconciliationSignal.TRIGGER_NOW, {"operations": [EXPIRE], "priority": "P0"}
            )
            await eventually(state, lambda s: s["raised_manual"] == [EXPIRE])

        hooks.append(raise_while_reporting)
        await client.start_workflow(
            TABLE_RECONCILIATION_WORKFLOW,
            TableReconciliationWorkflowInput(table_uuid=UUID),
            id=WORKFLOW_ID,
            task_queue=TASK_QUEUE,
            start_signal=TableReconciliationSignal.TABLE_MANAGED,
            start_signal_args=[{}],
        )

        async def requests() -> list[dict[str, Any]]:
            return list(plans.requests)

        second = (await eventually(requests, lambda r: len(r) >= 2, timeout=REAL_TIMEOUT_SECONDS))[1]
        assert (second["manual_operations"], second["manual_priority"]) == ([EXPIRE], "P0")

    _run(scenario)
