"""Define the PlanTableMaintenanceService."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.maintenance.maintenance_plan import MaintenancePlan
from application.domain.model.maintenance_settings.maintenance_settings import (
    MaintenanceSettings,
)
from application.domain.model.managed_table.table_status import TableStatus
from application.domain.model.managed_table.table_uuid import TableUuid
from application.domain.service.build_partition_filters import build_partition_filters
from application.domain.service.plan_manual_maintenance import plan_manual_maintenance
from application.domain.service.plan_scheduled_maintenance import (
    plan_scheduled_maintenance,
)
from application.exceptions import ValidationError
from application.port.inbound.reconcile.plan_table_maintenance import (
    PlanTableMaintenanceUseCase,
    PlanTableMaintenanceUseCaseInput,
    PlanTableMaintenanceUseCaseOutput,
    PlanTableMaintenanceUseCaseOutputFilterItem,
    PlanTableMaintenanceUseCaseOutputItem,
)
from application.port.outbound.catalog.read_catalog import ReadCatalogGatewayTableRef
from application.service.catalog.table_observation_from_gateway import (
    table_observation_from_gateway,
)
from application.service.reconcile.maintenance_procedure_args import (
    maintenance_procedure_args,
)
from application.service.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from application.domain.model.maintenance.planned_operation import (
        PlannedOperation,
    )
    from application.domain.model.managed_table.managed_table import ManagedTable
    from application.domain.model.observation.table_observation import (
        TableObservation,
    )
    from application.port.outbound.catalog.read_catalog import ReadCatalogGateway
    from application.port.outbound.managed_table.managed_tables_repo import (
        ManagedTablesRepo,
    )

logger = logging.getLogger(__name__)

_SKIP_REASONS = {
    TableStatus.DROPPED: "dropped",
    TableStatus.EXCLUDED: "excluded",
    TableStatus.PAUSED: "paused",
}


class PlanTableMaintenanceService(PlanTableMaintenanceUseCase):
    """Decide which maintenance operations a table needs right now."""

    def __init__(
        self, tables_repo: ManagedTablesRepo, catalog_gateway: ReadCatalogGateway
    ) -> None:
        """Bind the repo and the catalog gateway."""
        self._tables_repo = tables_repo
        self._catalog_gateway = catalog_gateway

    def execute(
        self, request: PlanTableMaintenanceUseCaseInput
    ) -> PlanTableMaintenanceUseCaseOutput:
        """Plan the due operations, or the requested ones for a manual trigger.

        ``now`` comes from the caller so that a workflow can supply a deterministic
        time. The result is a skip with a reason when the table is dropped, excluded,
        paused or gone from the catalog; otherwise it is planned, possibly empty.
        """
        manual = self._parse_manual(request.manual_operations)
        table = self._tables_repo.get(TableUuid(request.table_uuid))
        if table is None:
            return _skip("dropped", MaintenanceSettings(), None)
        settings = table.settings or MaintenanceSettings()
        reason = _SKIP_REASONS.get(table.status)
        if reason is not None:
            return _skip(reason, settings, table)
        ref = ReadCatalogGatewayTableRef(
            table.name.catalog, table.name.namespace, table.name.table
        )
        gateway_observation = self._catalog_gateway.observe_table(ref)
        with translate_domain_errors():
            observation = (
                None
                if gateway_observation is None
                else table_observation_from_gateway(gateway_observation)
            )
            if observation is None or observation.table_uuid != table.id.value:
                return _skip("not_found", settings, table)
            if manual is not None:
                plan = plan_manual_maintenance(manual)
            else:
                plan = plan_scheduled_maintenance(table, observation, request.now)
            return self._render(table, settings, plan, observation, request)

    def _render(
        self,
        table: ManagedTable,
        settings: MaintenanceSettings,
        plan: MaintenancePlan,
        observation: TableObservation,
        request: PlanTableMaintenanceUseCaseInput,
    ) -> PlanTableMaintenanceUseCaseOutput:
        properties = observation.properties
        operations = []
        for planned in plan.operations:
            filters: list[PlanTableMaintenanceUseCaseOutputFilterItem] = []
            if planned.partitions:
                filters = _partition_filters(table, observation, planned)
            operations.append(
                PlanTableMaintenanceUseCaseOutputItem(
                    operation=planned.operation.value,
                    filters=filters,
                    procedure_args=maintenance_procedure_args(
                        planned.operation, settings, properties, request.now
                    ),
                )
            )
        return PlanTableMaintenanceUseCaseOutput(
            status="planned",
            reason=None,
            reconcile_interval_seconds=_interval(settings),
            table_name=table.name.fully_qualified(),
            operations=operations,
        )

    @staticmethod
    def _parse_manual(raw: list[str] | None) -> list[MaintenanceOperation] | None:
        if raw is None:
            return None
        if not raw:
            raise ValidationError("manual_operations must not be empty")
        try:
            return [MaintenanceOperation(op) for op in raw]
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc


def _partition_filters(
    table: ManagedTable, observation: TableObservation, planned: PlannedOperation
) -> list[PlanTableMaintenanceUseCaseOutputFilterItem]:
    """Render the partition filters, or none (the whole table) if one cannot be.

    A partition field the filter builder does not support must not block the
    plan: that operation targets the whole table instead (R40).
    """
    try:
        built = build_partition_filters(
            table.name.catalog, observation.specs, planned.partitions
        )
    except ValueError as error:
        logger.warning(
            "cannot scope %s of %s to partitions (%s); compacting the whole table",
            planned.operation.value,
            table.name.qualified(),
            error,
        )
        return []
    return [
        PlanTableMaintenanceUseCaseOutputFilterItem(f.spec_id, f.where) for f in built
    ]


def _interval(settings: MaintenanceSettings) -> int:
    return int(settings.reconcile_interval.total_seconds())


def _skip(
    reason: str, settings: MaintenanceSettings, table: ManagedTable | None
) -> PlanTableMaintenanceUseCaseOutput:
    return PlanTableMaintenanceUseCaseOutput(
        status="skip",
        reason=reason,
        reconcile_interval_seconds=_interval(settings),
        table_name=None if table is None else table.name.fully_qualified(),
        operations=[],
    )
