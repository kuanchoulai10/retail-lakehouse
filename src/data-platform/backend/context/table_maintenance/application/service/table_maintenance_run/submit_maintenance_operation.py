"""Define the SubmitMaintenanceOperationService."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    InvalidRunTransition,
    TableMaintenanceRunId,
)
from context.table_maintenance.application.exceptions import (
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    SubmitMaintenanceOperationUseCase,
    SubmitMaintenanceOperationUseCaseInput,
    SubmitMaintenanceOperationUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    SubmitMaintenanceJobGatewayInput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        SubmitMaintenanceJobGateway,
        TableMaintenanceRunsRepo,
    )

logger = logging.getLogger(__name__)


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

    def execute(self, request: SubmitMaintenanceOperationUseCaseInput) -> SubmitMaintenanceOperationUseCaseOutput:
        """Record the attempt as running, submit the job, then attach its name.

        No job is submitted for an attempt the run rejects. The attempt is saved
        before the submit so a failed submit can still be recorded as a failure.
        The gateway deduplicates by ``(run_id, operation, attempt)`` and starting
        or attaching the same thing twice is a no-op, so a retried call leaves
        exactly one job. The run is read again after the submit, because the
        attempt can be recorded (for example as cancelled) while the submit runs;
        an attempt that is no longer running keeps its recorded outcome and the
        job name, which is informational, is dropped.
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
            run.start_attempt(operation, request.attempt, None, request.now)
            self._runs_repo.update(run)
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
        output = SubmitMaintenanceOperationUseCaseOutput(job_name=submitted.job_name)
        current = self._runs_repo.get(run.id)
        if current is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        try:
            current.attach_job_name(operation, request.attempt, submitted.job_name)
        except InvalidRunTransition as exc:
            logger.warning(
                "not attaching job %s to run %s: %s",
                submitted.job_name,
                request.run_id,
                exc,
            )
            return output
        with translate_domain_errors():
            self._runs_repo.update(current)
        return output
