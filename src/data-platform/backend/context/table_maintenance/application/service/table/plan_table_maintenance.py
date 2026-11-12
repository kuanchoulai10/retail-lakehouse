"""Define the PlanTableMaintenanceService."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceAssessment,
    MaintenanceOperation,
    MaintenancePlan,
    OperationVerdict,
)
from context.table_maintenance.application.domain.model.table import (
    TableId,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
)
from context.table_maintenance.application.domain.service.table import (
    assess_maintenance,
    build_partition_filters,
    plan_manual_maintenance,
)
from context.table_maintenance.application.exceptions import ValidationError
from context.table_maintenance.application.port.inbound.table import (
    PlanTableMaintenanceUseCase,
    PlanTableMaintenanceUseCaseInput,
    PlanTableMaintenanceUseCaseOutput,
    PlanTableMaintenanceUseCaseOutputCheckItem,
    PlanTableMaintenanceUseCaseOutputFilterItem,
    PlanTableMaintenanceUseCaseOutputItem,
    PlanTableMaintenanceUseCaseOutputMeasurementItem,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    ResolveApplicableTableMaintenancePolicyUseCase,
    ResolveApplicableTableMaintenancePolicyUseCaseInput,
    ResolveApplicableTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import TableMetadataRef
from context.table_maintenance.application.service.shared import applied_policy_ref_of, translate_domain_errors
from context.table_maintenance.application.service.table.table_observation_from_gateway import (
    table_observation_from_gateway,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    maintenance_procedure_args,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared import (
        PlannedOperation,
        TableObservation,
    )
    from context.table_maintenance.application.domain.model.table import Table
    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        TablesRepo,
    )

logger = logging.getLogger(__name__)

_SKIP_REASONS = {
    TableStatus.DROPPED: "dropped",
    TableStatus.UNMANAGED: "unmanaged",
}


class PlanTableMaintenanceService(PlanTableMaintenanceUseCase):
    """Decide which maintenance operations a table needs right now."""

    def __init__(
        self,
        tables_repo: TablesRepo,
        catalog_gateway: ReadTableMetadataGateway,
        resolve_applicable_policy: ResolveApplicableTableMaintenancePolicyUseCase,
    ) -> None:
        """Bind the repo, the catalog gateway and the applicable policy resolution."""
        self._tables_repo = tables_repo
        self._catalog_gateway = catalog_gateway
        self._resolve_applicable_policy = resolve_applicable_policy

    def execute(self, request: PlanTableMaintenanceUseCaseInput) -> PlanTableMaintenanceUseCaseOutput:
        """Plan the due operations, or the requested ones for a manual trigger.

        ``now`` comes from the caller so that a workflow can supply a deterministic
        time. The result is a skip with a reason when the table is dropped, unmanaged
        or gone from the catalog; otherwise it is planned, possibly empty.
        Every plan of a known table resolves the policy that applies to it, whose
        reconcile interval, dry run and operation policies it follows. A plan of a
        managed table first lifts the needs-attention marks set under an earlier
        applicable policy and saves the table when it lifted any.
        """
        manual = self._parse_manual(request.manual_operations)
        table = self._tables_repo.get(TableId(request.table_uuid))
        if table is None:
            return _skip_unknown_table()
        applied = self._resolve(table)
        policy = MaintenancePolicyContent.from_primitives(applied.content)
        reason = _SKIP_REASONS.get(table.status)
        if reason is not None:
            return _skip(reason, applied, policy, table)
        ref = TableMetadataRef(table.name.catalog, table.name.namespace, table.name.table)
        gateway_observation = self._catalog_gateway.observe_table(ref)
        with translate_domain_errors():
            observation = None if gateway_observation is None else table_observation_from_gateway(gateway_observation)
            if observation is None or observation.table_uuid != table.id.value:
                return _skip("not_found", applied, policy, table)
            if table.lift_attention_set_under_another_policy(applied_policy_ref_of(applied), request.now):
                self._tables_repo.update(table)
            if manual is not None:
                plan = plan_manual_maintenance(manual)
                checks = _manual_checks(manual)
            else:
                assessment = assess_maintenance(table, policy, observation, request.now)
                plan, checks = assessment.plan(), _scheduled_checks(assessment)
                if policy.dry_run:
                    plan = MaintenancePlan()
            return self._render(table, applied, policy, plan, checks, observation, request)

    def _resolve(self, table: Table) -> ResolveApplicableTableMaintenancePolicyUseCaseOutput:
        return self._resolve_applicable_policy.execute(
            ResolveApplicableTableMaintenancePolicyUseCaseInput(
                catalog=table.name.catalog,
                table_uuid=table.id.value,
                namespace=table.name.namespace,
                table=table.name.table,
            )
        )

    def _render(
        self,
        table: Table,
        applied: ResolveApplicableTableMaintenancePolicyUseCaseOutput,
        policy: MaintenancePolicyContent,
        plan: MaintenancePlan,
        checks: list[PlanTableMaintenanceUseCaseOutputCheckItem],
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
                    procedure_args=maintenance_procedure_args(planned.operation, policy, properties, request.now),
                    start_size=table.operation_state(planned.operation).start_size().value,
                )
            )
        return PlanTableMaintenanceUseCaseOutput(
            status="planned",
            reason=None,
            reconcile_interval_seconds=_interval(policy),
            table_name=table.name.fully_qualified(),
            operations=operations,
            dry_run=policy.dry_run,
            checks=checks,
            policy_name=applied.policy_name,
            policy_version=applied.version,
            policy_target=applied.target,
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
    table: Table, observation: TableObservation, planned: PlannedOperation
) -> list[PlanTableMaintenanceUseCaseOutputFilterItem]:
    """Render the partition filters, or none (the whole table) if one cannot be.

    A partition field the filter builder does not support must not block the
    plan: that operation targets the whole table instead (R40).
    """
    try:
        built = build_partition_filters(table.name.catalog, observation.specs, planned.partitions)
    except ValueError as error:
        logger.warning(
            "cannot scope %s of %s to partitions (%s); compacting the whole table",
            planned.operation.value,
            table.name.qualified(),
            error,
        )
        return []
    return [PlanTableMaintenanceUseCaseOutputFilterItem(f.spec_id, f.where) for f in built]


def _interval(policy: MaintenancePolicyContent) -> int:
    return int(policy.reconcile_interval.total_seconds())


_VERDICTS = {
    OperationVerdict.DUE: "due",
    OperationVerdict.NOT_DUE: "not_needed",
    OperationVerdict.COOLDOWN: "cooling_down",
    OperationVerdict.DISABLED: "off",
    OperationVerdict.NEEDS_ATTENTION: "needs_attention",
}


def _scheduled_checks(assessment: MaintenanceAssessment) -> list[PlanTableMaintenanceUseCaseOutputCheckItem]:
    return [
        PlanTableMaintenanceUseCaseOutputCheckItem(
            operation=a.operation.value,
            verdict=_VERDICTS[a.verdict],
            measurements=[
                PlanTableMaintenanceUseCaseOutputMeasurementItem(
                    key=m.key,
                    observed=m.observed,
                    unit=m.unit.value,
                    threshold=m.threshold,
                    comparison=None if m.comparison is None else m.comparison.value,
                    met=m.met,
                )
                for m in a.measurements
            ],
            next_eligible_at=a.next_eligible_at,
        )
        for a in assessment.operations
    ]


def _manual_checks(requested: list[MaintenanceOperation]) -> list[PlanTableMaintenanceUseCaseOutputCheckItem]:
    return [
        PlanTableMaintenanceUseCaseOutputCheckItem(
            operation=op.value,
            verdict="due" if op in requested else "not_checked",
            measurements=[],
            next_eligible_at=None,
        )
        for op in MaintenanceOperation.ordered()
    ]


def _skip(
    reason: str,
    applied: ResolveApplicableTableMaintenancePolicyUseCaseOutput,
    policy: MaintenancePolicyContent,
    table: Table,
) -> PlanTableMaintenanceUseCaseOutput:
    return PlanTableMaintenanceUseCaseOutput(
        status="skip",
        reason=reason,
        reconcile_interval_seconds=_interval(policy),
        table_name=table.name.fully_qualified(),
        operations=[],
        policy_name=applied.policy_name,
        policy_version=applied.version,
        policy_target=applied.target,
    )


def _skip_unknown_table() -> PlanTableMaintenanceUseCaseOutput:
    """Skip a table maintenance does not know; no policy applies, so the interval is the platform default's."""
    return PlanTableMaintenanceUseCaseOutput(
        status="skip",
        reason="dropped",
        reconcile_interval_seconds=_interval(MaintenancePolicyContent.platform_default()),
        table_name=None,
        operations=[],
        table_found=False,
    )
