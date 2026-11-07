"""Outbound ports for the table_maintenance_run group."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    OperationRun,
    OperationRunStatus,
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run.delete_maintenance_job.gateway import (
    DeleteMaintenanceJobGateway,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run.delete_maintenance_job.input import (
    DeleteMaintenanceJobGatewayInput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run.read_maintenance_job.gateway import (
    ReadMaintenanceJobGateway,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run.read_maintenance_job.input import (
    ReadMaintenanceJobGatewayInput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run.read_maintenance_job.output import (
    ReadMaintenanceJobGatewayOutput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run.send_maintenance_result.gateway import (
    SendMaintenanceResultGateway,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run.send_maintenance_result.input import (
    SendMaintenanceResultGatewayInput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run.submit_maintenance_job.gateway import (
    SubmitMaintenanceJobGateway,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run.submit_maintenance_job.input import (
    SubmitMaintenanceJobGatewayInput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run.submit_maintenance_job.output import (
    SubmitMaintenanceJobGatewayOutput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run.table_maintenance_runs_repo import (
    TableMaintenanceRunsRepo,
)

__all__ = [
    "MaintenanceOperation",
    "OperationRun",
    "OperationRunStatus",
    "TriggerType",
    "TableMaintenanceRunId",
    "DeleteMaintenanceJobGateway",
    "DeleteMaintenanceJobGatewayInput",
    "ReadMaintenanceJobGateway",
    "ReadMaintenanceJobGatewayInput",
    "ReadMaintenanceJobGatewayOutput",
    "SendMaintenanceResultGateway",
    "SendMaintenanceResultGatewayInput",
    "SubmitMaintenanceJobGateway",
    "SubmitMaintenanceJobGatewayInput",
    "SubmitMaintenanceJobGatewayOutput",
    "TableId",
    "TableMaintenanceRun",
    "TableMaintenanceRunsRepo",
]
