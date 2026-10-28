"""Outbound ports for the table_maintenance_run group."""

from __future__ import annotations

from application.domain.model.table import TableId
from application.domain.model.table_maintenance_run import TableMaintenanceRun
from application.port.outbound.table_maintenance_run.delete_maintenance_job.gateway import (
    DeleteMaintenanceJobGateway,
)
from application.port.outbound.table_maintenance_run.delete_maintenance_job.input import (
    DeleteMaintenanceJobGatewayInput,
)
from application.port.outbound.table_maintenance_run.read_maintenance_job.gateway import (
    ReadMaintenanceJobGateway,
)
from application.port.outbound.table_maintenance_run.read_maintenance_job.input import (
    ReadMaintenanceJobGatewayInput,
)
from application.port.outbound.table_maintenance_run.read_maintenance_job.output import (
    ReadMaintenanceJobGatewayOutput,
)
from application.port.outbound.table_maintenance_run.send_maintenance_result.gateway import (
    SendMaintenanceResultGateway,
)
from application.port.outbound.table_maintenance_run.send_maintenance_result.input import (
    SendMaintenanceResultGatewayInput,
)
from application.port.outbound.table_maintenance_run.submit_maintenance_job.gateway import (
    SubmitMaintenanceJobGateway,
)
from application.port.outbound.table_maintenance_run.submit_maintenance_job.input import (
    SubmitMaintenanceJobGatewayInput,
)
from application.port.outbound.table_maintenance_run.submit_maintenance_job.output import (
    SubmitMaintenanceJobGatewayOutput,
)
from application.port.outbound.table_maintenance_run.table_maintenance_runs_repo import (
    TableMaintenanceRunsRepo,
)

__all__ = [
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
