"""Temporal contracts of the table discovery workflow."""

from __future__ import annotations

from adapter.hybrid.temporal.contracts.table_discovery.activity import (
    TableDiscoveryActivity,
)
from adapter.hybrid.temporal.contracts.table_discovery.schedule_id import (
    TABLE_DISCOVERY_SCHEDULE_ID_PREFIX,
    table_discovery_schedule_id,
)
from adapter.hybrid.temporal.contracts.table_discovery.summary import (
    table_discovery_summary,
)
from adapter.hybrid.temporal.contracts.table_discovery.workflow_id import (
    table_discovery_adhoc_workflow_id,
)
from adapter.hybrid.temporal.contracts.table_discovery.workflow_input import (
    TableDiscoveryWorkflowInput,
)
from adapter.hybrid.temporal.contracts.table_discovery.workflow_name import (
    TABLE_DISCOVERY_WORKFLOW,
)

__all__ = [
    "TABLE_DISCOVERY_SCHEDULE_ID_PREFIX",
    "TABLE_DISCOVERY_WORKFLOW",
    "TableDiscoveryActivity",
    "TableDiscoveryWorkflowInput",
    "table_discovery_adhoc_workflow_id",
    "table_discovery_schedule_id",
    "table_discovery_summary",
]
