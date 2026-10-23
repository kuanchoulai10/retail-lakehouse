"""Define the SubmitMaintenanceOperationService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.maintenance_run.maintenance_run_id import (
    MaintenanceRunId,
)
from application.domain.service.spark_application_name import spark_application_name
from application.exceptions import NotFoundError, ValidationError
from application.port.inbound.reconcile.submit_maintenance_operation import (
    SubmitMaintenanceOperationUseCase,
    SubmitMaintenanceOperationUseCaseInput,
    SubmitMaintenanceOperationUseCaseOutput,
)
from application.port.outbound.spark.submit_maintenance_job import (
    SubmitMaintenanceJobGatewayInput,
)
from application.service.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from application.port.outbound.maintenance_run.maintenance_runs_repo import (
        MaintenanceRunsRepo,
    )
    from application.port.outbound.managed_table.managed_tables_repo import (
        ManagedTablesRepo,
    )
    from application.port.outbound.spark.submit_maintenance_job import (
        SubmitMaintenanceJobGateway,
    )


class SubmitMaintenanceOperationService(SubmitMaintenanceOperationUseCase):
    """Record an attempt on the run and submit its Spark job."""

    def __init__(
        self,
        runs_repo: MaintenanceRunsRepo,
        tables_repo: ManagedTablesRepo,
        submit_gateway: SubmitMaintenanceJobGateway,
    ) -> None:
        """Bind the repos and the submit gateway."""
        self._runs_repo = runs_repo
        self._tables_repo = tables_repo
        self._submit_gateway = submit_gateway

    def execute(
        self, request: SubmitMaintenanceOperationUseCaseInput
    ) -> SubmitMaintenanceOperationUseCaseOutput:
        """Start the attempt, save the run, then submit the job.

        The attempt is a no-op when already started and the gateway deduplicates by
        application name, so a retried call leaves exactly one job.
        """
        try:
            operation = MaintenanceOperation(request.operation)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        run = self._runs_repo.get(MaintenanceRunId(request.run_id))
        if run is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        table = self._tables_repo.get(run.table_uuid)
        if table is None:
            raise NotFoundError(f"managed table {run.table_uuid.value} not found")
        with translate_domain_errors():
            app_name = spark_application_name(
                request.run_id, operation, request.attempt
            )
            run.start_attempt(operation, request.attempt, app_name, request.now)
            self._runs_repo.update(run)
        wheres = [f.where for f in request.filters]
        self._submit_gateway.submit(
            SubmitMaintenanceJobGatewayInput(
                app_name=app_name,
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
                    f"/v1/runs/{request.run_id}/operations/{operation.value}/result"
                ),
            )
        )
        return SubmitMaintenanceOperationUseCaseOutput(app_name=app_name)
