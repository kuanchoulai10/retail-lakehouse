"""Define the PlanTableMaintenanceService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceAssessment,
    MaintenanceOperation,
    MaintenancePlan,
    OperationVerdict,
    TablePriority,
)
from context.table_maintenance.application.domain.model.table import (
    DEFAULT_OPERATION_COOLDOWNS,
    TableId,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
)
from context.table_maintenance.application.domain.service.table import (
    assess_maintenance,
    plan_manual_maintenance,
)
from context.table_maintenance.application.exceptions import ValidationError
from context.table_maintenance.application.port.inbound.table import (
    PlanTableMaintenanceUseCase,
    PlanTableMaintenanceUseCaseInput,
    PlanTableMaintenanceUseCaseOutput,
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
    from collections.abc import Sequence
    from datetime import datetime

    from context.table_maintenance.application.domain.model.shared import TableObservation
    from context.table_maintenance.application.domain.model.table import OperationCooldowns, Table
    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        TablesRepo,
    )

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
        *,
        cooldowns: OperationCooldowns = DEFAULT_OPERATION_COOLDOWNS,
    ) -> None:
        """Bind the tables repo, the catalog gateway and the applicable policy resolution.

        ``cooldowns`` are the platform's cooldown of each operation and the cap where the doubling
        of a failing operation's cooldown stops.
        """
        self._tables_repo = tables_repo
        self._catalog_gateway = catalog_gateway
        self._resolve_applicable_policy = resolve_applicable_policy
        self._cooldowns = cooldowns

    def execute(self, request: PlanTableMaintenanceUseCaseInput) -> PlanTableMaintenanceUseCaseOutput:
        """Plan the due operations, or the requested ones for a manual trigger.

        ``now`` comes from the caller so that a workflow can supply a deterministic
        time. The result is a skip with a reason when the table is dropped, unmanaged
        or gone from the catalog; otherwise it is planned, possibly empty.
        Every plan of a known table resolves the policy that applies to it, whose
        schedule interval, dry run and operation blocks it follows. A plan of a
        managed table first lifts the needs-attention marks set under an earlier
        applicable policy and saves the table when it lifted any. A plan that
        observes the table saves its newest commit when that moves its last commit.

        Every planned operation targets the whole table (no filters) and starts at
        the size the table remembers for it; a due compaction rewrites the whole
        table with the policy's rewrite options, however many partitions qualify; an operation
        the policy leaves out is never due, and a manual run of it runs with the platform's defaults.
        """
        manual = self._parse_manual(request.manual_operations)
        manual_priority = self._parse_manual_priority(request.manual_priority)
        table = self._tables_repo.get(TableId(request.table_uuid))
        if table is None:
            return _skip_unknown_table()
        applied = self._resolve(table)
        policy = MaintenancePolicyContent.from_primitives(applied.content)
        reason = _SKIP_REASONS.get(table.status)
        if reason is not None:
            return _skip(reason, applied, policy, table, manual_priority)
        ref = TableMetadataRef(table.name.catalog, table.name.namespace, table.name.table)
        gateway_observation = self._catalog_gateway.observe_table(ref)
        with translate_domain_errors():
            observation = None if gateway_observation is None else table_observation_from_gateway(gateway_observation)
            if observation is None or observation.table_uuid != table.id.value:
                return _skip("not_found", applied, policy, table, manual_priority)
            self._record_last_commit(table, observation.last_committed_at)
            self._lift_stale_marks(table, applied, request.now)
            if manual is not None:
                plan = plan_manual_maintenance(manual)
                checks = _manual_checks(manual)
            else:
                assessment = assess_maintenance(table, policy, observation, request.now, cooldowns=self._cooldowns)
                plan, checks = assessment.plan(), _scheduled_checks(assessment)
                if policy.dry_run:
                    plan = MaintenancePlan()
            return self._render(table, applied, policy, plan, checks, observation, request, manual_priority)

    def _lift_stale_marks(
        self, table: Table, applied: ResolveApplicableTableMaintenancePolicyUseCaseOutput, now: datetime
    ) -> None:
        """Lift the marks set under another policy than ``applied``, on ``table`` and on the stored table.

        The stored table is read again right before it is saved, since the catalog read in between
        is slow and a rename, unmanage or drop may land meanwhile; a table dropped by then is left.
        """
        ref = applied_policy_ref_of(applied)
        if not table.lift_attention_set_under_another_policy(ref, now):
            return
        stored = self._tables_repo.get(table.id)
        if stored is None or stored.status == TableStatus.DROPPED:
            return
        if stored.lift_attention_set_under_another_policy(ref, now):
            self._tables_repo.update(stored)

    def _record_last_commit(self, table: Table, at: datetime | None) -> None:
        """Write the newest commit the observation saw, when it is newer than the table read.

        Only the last commit is written, and the store applies the same rule again, so a rename,
        unmanage, drop or recorded result landed during the catalog read is never put back.
        """
        if at is not None and table.record_last_commit(at):
            self._tables_repo.record_last_commit(table.id, at)

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
        checks: tuple[PlanTableMaintenanceUseCaseOutput.Check, ...],
        observation: TableObservation,
        request: PlanTableMaintenanceUseCaseInput,
        manual_priority: TablePriority | None,
    ) -> PlanTableMaintenanceUseCaseOutput:
        properties = observation.properties
        operations = tuple(
            PlanTableMaintenanceUseCaseOutput.Operation(
                operation=planned.operation.value,
                filters=(),
                procedure_args=maintenance_procedure_args(planned.operation, policy, properties, request.now),
                start_size=table.operation_state(planned.operation).start_size().value,
            )
            for planned in plan.operations
        )
        return PlanTableMaintenanceUseCaseOutput(
            status="planned",
            reason=None,
            reconcile_interval_seconds=_interval(policy),
            table_name=table.name.fully_qualified(),
            operations=operations,
            dry_run=policy.dry_run,
            checks=checks,
            policy_id=applied.policy_id,
            policy_name=applied.policy_name,
            policy_version=applied.version,
            policy_target=applied.target,
            priority=_priority_of(table, manual_priority),
        )

    @staticmethod
    def _parse_manual(raw: Sequence[str] | None) -> list[MaintenanceOperation] | None:
        if raw is None:
            return None
        if not raw:
            raise ValidationError("manual_operations must not be empty")
        try:
            return [MaintenanceOperation(op) for op in raw]
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    @staticmethod
    def _parse_manual_priority(raw: str | None) -> TablePriority | None:
        if raw is None:
            return None
        try:
            return TablePriority(raw)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc


def _priority_of(table: Table, manual_priority: TablePriority | None) -> str:
    """Return the priority a run of ``table`` gets: the manual one when given, else the table's own."""
    return (manual_priority or table.priority).value


def _interval(policy: MaintenancePolicyContent) -> int:
    """Return the schedule interval of ``policy`` in seconds, which the reconciliation waits between checks."""
    return int(policy.on.schedule.every.total_seconds())


_VERDICTS = {
    OperationVerdict.DUE: "due",
    OperationVerdict.NOT_DUE: "not_needed",
    OperationVerdict.COOLDOWN: "cooling_down",
    OperationVerdict.DISABLED: "off",
    OperationVerdict.NEEDS_ATTENTION: "needs_attention",
}


def _scheduled_checks(assessment: MaintenanceAssessment) -> tuple[PlanTableMaintenanceUseCaseOutput.Check, ...]:
    return tuple(
        PlanTableMaintenanceUseCaseOutput.Check(
            operation=a.operation.value,
            verdict=_VERDICTS[a.verdict],
            measurements=tuple(
                PlanTableMaintenanceUseCaseOutput.Measurement(
                    key=m.key,
                    observed=m.observed,
                    unit=m.unit.value,
                    threshold=m.threshold,
                    comparison=None if m.comparison is None else m.comparison.value,
                    met=m.met,
                )
                for m in a.measurements
            ),
            next_eligible_at=a.next_eligible_at,
        )
        for a in assessment.operations
    )


def _manual_checks(requested: list[MaintenanceOperation]) -> tuple[PlanTableMaintenanceUseCaseOutput.Check, ...]:
    return tuple(
        PlanTableMaintenanceUseCaseOutput.Check(
            operation=op.value,
            verdict="due" if op in requested else "not_checked",
            measurements=(),
            next_eligible_at=None,
        )
        for op in MaintenanceOperation.ordered()
    )


def _skip(
    reason: str,
    applied: ResolveApplicableTableMaintenancePolicyUseCaseOutput,
    policy: MaintenancePolicyContent,
    table: Table,
    manual_priority: TablePriority | None,
) -> PlanTableMaintenanceUseCaseOutput:
    return PlanTableMaintenanceUseCaseOutput(
        status="skip",
        reason=reason,
        reconcile_interval_seconds=_interval(policy),
        table_name=table.name.fully_qualified(),
        operations=(),
        policy_id=applied.policy_id,
        policy_name=applied.policy_name,
        policy_version=applied.version,
        policy_target=applied.target,
        priority=_priority_of(table, manual_priority),
    )


def _skip_unknown_table() -> PlanTableMaintenanceUseCaseOutput:
    """Skip a table maintenance does not know; no policy applies, so the interval is the platform default's."""
    return PlanTableMaintenanceUseCaseOutput(
        status="skip",
        reason="dropped",
        reconcile_interval_seconds=_interval(MaintenancePolicyContent.platform_default()),
        table_name=None,
        operations=(),
        table_found=False,
    )
