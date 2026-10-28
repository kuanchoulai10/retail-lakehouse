"""Define the SubmitMaintenanceOperationService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.table_maintenance_run.table_maintenance_run_id import (
    TableMaintenanceRunId,
)
from application.exceptions import NotFoundError, ValidationError
from application.port.inbound.table_maintenance_run.submit_maintenance_operation import (
    SubmitMaintenanceOperationUseCase,
    SubmitMaintenanceOperationUseCaseInput,
    SubmitMaintenanceOperationUseCaseOutput,
)
from application.port.outbound.table_maintenance_run.submit_maintenance_job import (
    SubmitMaintenanceJobGatewayInput,
)
from application.service.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from application.port.outbound.table_maintenance_run.table_maintenance_runs_repo import (
        TableMaintenanceRunsRepo,
    )
    from application.port.outbound.table.tables_repo import (
        TablesRepo,
    )
    from application.port.outbound.table_maintenance_run.submit_maintenance_job import (
        SubmitMaintenanceJobGateway,
    )


class SubmitMaintenanceOperationService(SubmitMaintenanceOperationUseCase):
    """Submit the job of an attempt and record the attempt on the run."""

    def __init__(
        self,
        runs_repo: TableMaintenanceRunsRepo,
        tables_repo: TablesRepo,
        submit_gateway: SubmitMaintenanceJobGateway,
    ) -> None:
        """Bind the repos and the submit gateway."""
        self._runs_repo = runs_repo
        self._tables_repo = tables_repo
        self._submit_gateway = submit_gateway

    def execute(
        self, request: SubmitMaintenanceOperationUseCaseInput
    ) -> SubmitMaintenanceOperationUseCaseOutput:
        """Check the attempt, submit the job, then record the attempt on the run.

        No job is submitted for an attempt the run would reject. The gateway
        deduplicates by ``(run_id, operation, attempt)`` and recording an attempt
        that is already running with the same job name is a no-op, so a retried
        call leaves exactly one job.
        """
        try:
            operation = MaintenanceOperation(request.operation)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        run = self._runs_repo.get(TableMaintenanceRunId(request.run_id))
        if run is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        table = self._tables_repo.get(run.table_uuid)
        if table is None:
            raise NotFoundError(f"table {run.table_uuid.value} not found")
        with translate_domain_errors():
            run.ensure_attempt_startable(operation, request.attempt)
        wheres = [f.where for f in request.filters]
        submitted = self._submit_gateway.submit(
            SubmitMaintenanceJobGatewayInput(
                run_id=request.run_id,
                operation=operation.value,
                attempt=request.attempt,
                catalog=table.name.catalog,
                namespace=table.name.namespace,
                table=table.name.table,
                where=[] if not all(wheres) else wheres,
                procedure_args=dict(request.procedure_args),
                callback_url=(
                    f"{request.callback_base_url.rstrip('/')}"
                    f"/v1/table-maintenance-runs/{request.run_id}"
                    f"/operations/{operation.value}/result"
                ),
            )
        )
        with translate_domain_errors():
            run.start_attempt(
                operation, request.attempt, submitted.job_name, request.now
            )
            self._runs_repo.update(run)
        return SubmitMaintenanceOperationUseCaseOutput(job_name=submitted.job_name)
