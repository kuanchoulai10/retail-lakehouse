"""Define the PlanTableMaintenanceService."""

from __future__ import annotations

import logging
import math
from dataclasses import replace
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateSelection,
    CandidateShortfall,
)
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceAssessment,
    MaintenanceOperation,
    MaintenancePlan,
    OperationVerdict,
    PlannedOperation,
)
from context.table_maintenance.application.domain.model.table import (
    TableId,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId
from context.table_maintenance.application.domain.service.compaction_candidate import (
    estimate_throughput,
    observe_compaction_partitions,
    pick_compaction_candidates,
)
from context.table_maintenance.application.domain.service.shared import size_for_bytes
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
    PlanTableMaintenanceUseCaseOutputCandidatePartitionItem,
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
from context.table_maintenance.application.service.table.compaction_share import CompactionShare
from context.table_maintenance.application.service.table.table_observation_from_gateway import (
    table_observation_from_gateway,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    maintenance_procedure_args,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime, timedelta

    from context.table_maintenance.application.domain.model.compaction_candidate import CompactionCandidate
    from context.table_maintenance.application.domain.model.shared import (
        PartitionStats,
        SizeMemory,
        TableObservation,
    )
    from context.table_maintenance.application.domain.model.table import Table
    from context.table_maintenance.application.port.outbound.compaction_candidate import CompactionCandidatesRepo
    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        TablesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run import TableMaintenanceRunsRepo

logger = logging.getLogger(__name__)

_COMPACTION = MaintenanceOperation.REWRITE_DATA_FILES
_GIB = 1024**3
_FALLBACK_MEMORY_GB = 1.5
_RUNS_FOR_THROUGHPUT = 50

_SKIP_REASONS = {
    TableStatus.DROPPED: "dropped",
    TableStatus.UNMANAGED: "unmanaged",
}


class PlanTableMaintenanceService(PlanTableMaintenanceUseCase):
    """Decide which maintenance operations a table needs right now."""

    def __init__(  # noqa: PLR0913
        self,
        tables_repo: TablesRepo,
        catalog_gateway: ReadTableMetadataGateway,
        resolve_applicable_policy: ResolveApplicableTableMaintenancePolicyUseCase,
        candidates_repo: CompactionCandidatesRepo,
        runs_repo: TableMaintenanceRunsRepo,
        *,
        selection: CandidateSelection,
        size_memory: Mapping[ComputeSize, SizeMemory],
        claim_lease: timedelta,
    ) -> None:
        """Bind the repos, the catalog gateway, the applicable policy resolution and how candidates are picked.

        ``size_memory`` gives the memory each compute size runs with, for the cost
        estimate; ``claim_lease`` is how long a run holds the candidates it claims.
        """
        self._tables_repo = tables_repo
        self._catalog_gateway = catalog_gateway
        self._resolve_applicable_policy = resolve_applicable_policy
        self._candidates_repo = candidates_repo
        self._runs_repo = runs_repo
        self._selection = selection
        self._size_memory = dict(size_memory)
        self._claim_lease = claim_lease

    def execute(self, request: PlanTableMaintenanceUseCaseInput) -> PlanTableMaintenanceUseCaseOutput:
        """Plan the due operations, or the requested ones for a manual trigger.

        ``now`` comes from the caller so that a workflow can supply a deterministic
        time. The result is a skip with a reason when the table is dropped, unmanaged
        or gone from the catalog; otherwise it is planned, possibly empty.
        Every plan of a known table resolves the policy that applies to it, whose
        reconcile interval, dry run and operation policies it follows. A plan of a
        managed table first lifts the needs-attention marks set under an earlier
        applicable policy and saves the table when it lifted any.

        A scheduled plan also brings the table's compaction candidates in line with
        the observation, whatever is due, with the policy's priority; when
        compaction is not due (or the policy is a dry run) they are held as not
        due. A due compaction takes only the best candidates a compaction round
        granted the table, claimed for ``run_id``; when it can take none (none
        granted yet, all held or claimed) it is not planned and its check says
        why. A manual plan leaves the candidates alone, and a skipped table loses
        them.
        """
        manual = self._parse_manual(request.manual_operations)
        table = self._tables_repo.get(TableId(request.table_uuid))
        if table is None:
            self._candidates_repo.delete_by_table(TableId(request.table_uuid))
            return _skip_unknown_table()
        applied = self._resolve(table)
        policy = MaintenancePolicyContent.from_primitives(applied.content)
        reason = _SKIP_REASONS.get(table.status)
        if reason is not None:
            self._candidates_repo.delete_by_table(table.id)
            return _skip(reason, applied, policy, table)
        ref = TableMetadataRef(table.name.catalog, table.name.namespace, table.name.table)
        gateway_observation = self._catalog_gateway.observe_table(ref)
        with translate_domain_errors():
            observation = None if gateway_observation is None else table_observation_from_gateway(gateway_observation)
            if observation is None or observation.table_uuid != table.id.value:
                self._candidates_repo.delete_by_table(table.id)
                return _skip("not_found", applied, policy, table)
            self._lift_stale_marks(table, applied, request.now)
            if manual is not None:
                plan = plan_manual_maintenance(manual)
                checks = _manual_checks(manual)
                compaction = CompactionShare()
            else:
                assessment = assess_maintenance(table, policy, observation, request.now)
                plan, checks = assessment.plan(), _scheduled_checks(assessment)
                cooling_down = any(
                    a.operation is _COMPACTION and a.verdict is OperationVerdict.COOLDOWN for a in assessment.operations
                )
                plan, checks, compaction = self._share_compaction(
                    table, policy, observation, plan, checks, request, cooling_down=cooling_down
                )
                if policy.dry_run:
                    plan = MaintenancePlan()
            return self._render(table, applied, policy, plan, checks, observation, request, compaction)

    def _share_compaction(  # noqa: PLR0913
        self,
        table: Table,
        policy: MaintenancePolicyContent,
        observation: TableObservation,
        plan: MaintenancePlan,
        checks: list[PlanTableMaintenanceUseCaseOutputCheckItem],
        request: PlanTableMaintenanceUseCaseInput,
        *,
        cooling_down: bool,
    ) -> tuple[MaintenancePlan, list[PlanTableMaintenanceUseCaseOutputCheckItem], CompactionShare]:
        """Sync the candidates, and narrow a due compaction to the granted candidates it takes or drop it.

        A compaction that is only ``cooling_down`` holds its candidates in
        cooldown, keeping their wait for a round; a dry run, needs attention or
        an unmet trigger holds them not due, ending it.
        """
        due = next((p for p in plan.operations if p.operation is _COMPACTION), None)
        runs = self._runs_repo.list_by_table(table.id, limit=_RUNS_FOR_THROUGHPUT)
        remembered = table.operation_state(_COMPACTION).start_size()
        claim_for = None if request.run_id is None else TableMaintenanceRunId(request.run_id)
        existing = self._candidates_repo.list_by_table(table.id)
        pick = pick_compaction_candidates(
            table.id,
            existing,
            observe_compaction_partitions(policy, observation),
            selection=self._selection,
            memory_gb=self._memory_gb(remembered),
            throughput_bytes_per_hour=estimate_throughput(
                runs,
                default_bytes_per_hour=self._selection.default_throughput_bytes_per_hour,
                min_sample_bytes=self._selection.min_throughput_sample_bytes,
            ),
            released_runs=self._released_runs(existing, claim_for),
            pick=due is not None and not policy.dry_run,
            priority=policy.priority,
            cooling_down=cooling_down and not policy.dry_run,
            claim_for=claim_for,
            lease_until=request.now + self._claim_lease,
            now=request.now,
        )
        if pick.removed:
            self._candidates_repo.delete(pick.removed)
        if pick.saved:
            self._candidates_repo.save_all(pick.saved)
        if due is None or policy.dry_run:
            return plan, checks, CompactionShare()
        if pick.shortfall is not None:
            kept = tuple(p for p in plan.operations if p.operation is not _COMPACTION)
            checks = [
                replace(c, verdict=pick.shortfall.value, next_eligible_at=pick.next_eligible_at)
                if c.operation == _COMPACTION.value
                else c
                for c in checks
            ]
            next_check_at = pick.next_eligible_at if pick.shortfall is CandidateShortfall.ALL_HELD else None
            return MaintenancePlan(operations=kept), checks, CompactionShare(next_check_at=next_check_at)
        narrowed = PlannedOperation(operation=_COMPACTION, partitions=_partitions_of(pick.selected, observation))
        plan = MaintenancePlan(operations=tuple(narrowed if p is due else p for p in plan.operations))
        picked_size = size_for_bytes(
            sum(c.score.data_bytes for c in pick.selected),
            s_max_bytes=self._selection.size_s_max_bytes,
            m_max_bytes=self._selection.size_m_max_bytes,
        )
        return plan, checks, CompactionShare(candidates=pick.selected, start_size=remembered.at_least(picked_size))

    def _released_runs(
        self, existing: Sequence[CompactionCandidate], claim_for: TableMaintenanceRunId | None
    ) -> frozenset[TableMaintenanceRunId]:
        """Return the runs, other than the one planned for, whose claims are handed back.

        A run that has finished keeps no claim. Neither does a run with no run
        record: the reconciliation plans only when no run of the table is in
        flight, so such a claim comes from a plan that saved it and then failed,
        and its run never started. Each holder is looked up, so the release does
        not depend on how many recent runs are read for the throughput.
        """
        holders = {
            c.claimed_by_run_id
            for c in existing
            if c.state.holds_a_claim and c.claimed_by_run_id is not None and c.claimed_by_run_id != claim_for
        }
        released: set[TableMaintenanceRunId] = set()
        for run_id in holders:
            run = self._runs_repo.get(run_id)
            if run is None or run.finished_at is not None:
                released.add(run_id)
        return frozenset(released)

    def _memory_gb(self, size: ComputeSize) -> float:
        """Return the GiB of memory a compaction at ``size`` holds: its driver's and one executor's heap."""
        memory = self._size_memory.get(size)
        if memory is None:
            return _FALLBACK_MEMORY_GB
        return (memory.driver_bytes + memory.executor_bytes) / _GIB

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
        compaction: CompactionShare,
    ) -> PlanTableMaintenanceUseCaseOutput:
        properties = observation.properties
        operations = []
        for planned in plan.operations:
            filters: list[PlanTableMaintenanceUseCaseOutputFilterItem] = []
            if planned.partitions:
                filters = _partition_filters(table, observation, planned)
            start_size = table.operation_state(planned.operation).start_size()
            candidates: tuple[CompactionCandidate, ...] = ()
            filter_sets: list[list[PlanTableMaintenanceUseCaseOutputFilterItem]] = []
            if planned.operation is _COMPACTION:
                start_size = compaction.start_size or start_size
                candidates = compaction.candidates
                if filters:
                    filter_sets = _filter_sets(table, observation, candidates)
            operations.append(
                PlanTableMaintenanceUseCaseOutputItem(
                    operation=planned.operation.value,
                    filters=filters,
                    procedure_args=maintenance_procedure_args(planned.operation, policy, properties, request.now),
                    start_size=start_size.value,
                    candidate_partitions=[
                        PlanTableMaintenanceUseCaseOutputCandidatePartitionItem(
                            c.partition.spec_id, list(c.partition.values)
                        )
                        for c in candidates
                    ],
                    filter_sets=filter_sets,
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
            next_check_at=compaction.next_check_at,
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


def _partitions_of(
    candidates: tuple[CompactionCandidate, ...], observation: TableObservation
) -> tuple[PartitionStats, ...]:
    """Return the observed partitions the candidates stand for, or none (the whole table) for a whole-table one."""
    if any(c.partition.is_whole_table for c in candidates):
        return ()
    observed = {(p.spec_id, p.values): p for p in observation.partitions}
    keys = [(c.partition.spec_id, c.partition.values) for c in candidates]
    return tuple(observed[k] for k in keys if k in observed)


def _filter_sets(
    table: Table, observation: TableObservation, candidates: tuple[CompactionCandidate, ...]
) -> list[list[PlanTableMaintenanceUseCaseOutputFilterItem]]:
    """Return the filters of all candidates, the best half and the best quarter (rounded up), each count once."""
    counts = dict.fromkeys(math.ceil(len(candidates) / d) for d in (1, 2, 4))
    return [
        _partition_filters(
            table,
            observation,
            PlannedOperation(operation=_COMPACTION, partitions=_partitions_of(candidates[:count], observation)),
        )
        for count in counts
    ]


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
