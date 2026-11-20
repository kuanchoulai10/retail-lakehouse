"""Define the GetPlatformSettingsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    GetPlatformSettingsUseCase,
    GetPlatformSettingsUseCaseInput,
    GetPlatformSettingsUseCaseOutput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared import (
        PlatformComputeSize,
        PlatformPriority,
        PlatformSettings,
    )

_SECONDS = "seconds"


def _item(
    key: str, label: str, value: float | str, unit: str | None, description: str
) -> GetPlatformSettingsUseCaseOutput.Setting:
    return GetPlatformSettingsUseCaseOutput.Setting(
        key=key, label=label, value=value, unit=unit, description=description
    )


class GetPlatformSettingsService(GetPlatformSettingsUseCase):
    """Report the platform-level settings the running component was started with, grouped by theme.

    Every label and description is written here, so the API and the console cannot drift
    apart. Only what ``PlatformSettings`` holds is listed.
    """

    def __init__(self, settings: PlatformSettings) -> None:
        """Bind the settings the component was started with."""
        self._settings = settings

    def execute(self, request: GetPlatformSettingsUseCaseInput) -> GetPlatformSettingsUseCaseOutput:  # noqa: ARG002
        """Return the five groups of settings in the order the console shows them."""
        settings = self._settings
        return GetPlatformSettingsUseCaseOutput(
            groups=(
                GetPlatformSettingsUseCaseOutput.Group(
                    key="execution_capacity",
                    title="Execution capacity",
                    items=_execution_capacity(settings),
                ),
                GetPlatformSettingsUseCaseOutput.Group(
                    key="compute_sizes",
                    title="Spark sizes",
                    items=tuple(item for size in settings.compute_sizes for item in _compute_size(size)),
                ),
                GetPlatformSettingsUseCaseOutput.Group(
                    key="compaction_scheduling",
                    title="Compaction scheduling",
                    items=_compaction_scheduling(settings),
                ),
                GetPlatformSettingsUseCaseOutput.Group(
                    key="cooldown_and_backoff",
                    title="Cooldown and backoff",
                    items=(
                        _item(
                            "maintenance_failure_backoff_cap_seconds",
                            "Failure backoff cap",
                            settings.failure_backoff_cap_seconds,
                            _SECONDS,
                            "Each failure of an operation doubles its cooldown, up to this limit.",
                        ),
                    ),
                ),
                GetPlatformSettingsUseCaseOutput.Group(
                    key="discovery",
                    title="Discovery",
                    items=(
                        _item(
                            "discovery_interval_seconds",
                            "Scan interval",
                            settings.discovery_interval_seconds,
                            _SECONDS,
                            "How often discovery scans the catalogs for tables to manage.",
                        ),
                    ),
                ),
            )
        )


def _execution_capacity(settings: PlatformSettings) -> tuple[GetPlatformSettingsUseCaseOutput.Setting, ...]:
    return (
        _item(
            "maintenance_attempt_deadline_seconds",
            "Attempt time limit",
            settings.attempt_deadline_seconds,
            _SECONDS,
            "How long one attempt may run once its Spark job has started; time spent waiting in the queue does not "
            "count.",
        ),
        _item(
            "maintenance_queue_wait_limit_seconds",
            "Queue wait limit",
            settings.queue_wait_limit_seconds,
            _SECONDS,
            "How long one attempt may wait in its Volcano queue before it is stopped; its operation then waits for the "
            "next plan.",
        ),
        _item(
            "maintenance_max_attempts",
            "Attempts per operation",
            settings.max_attempts,
            "attempts",
            "How many times one run tries an operation before it gives the operation up as failed.",
        ),
    )


def _compute_size(size: PlatformComputeSize) -> tuple[GetPlatformSettingsUseCaseOutput.Setting, ...]:
    name = size.size.value
    prefix = f"compute_size_{name.lower()}"
    return (
        _item(
            f"{prefix}_driver_memory",
            f"{name} driver memory",
            size.driver_memory,
            None,
            f"The memory of the Spark driver when an operation runs at size {name}.",
        ),
        _item(
            f"{prefix}_executor_memory",
            f"{name} executor memory",
            size.executor_memory,
            None,
            f"The memory of each Spark executor when an operation runs at size {name}.",
        ),
        _item(
            f"{prefix}_executor_instances",
            f"{name} executors",
            size.executor_instances,
            "executors",
            f"How many Spark executors an operation gets when it runs at size {name}.",
        ),
    )


def _compaction_scheduling(settings: PlatformSettings) -> tuple[GetPlatformSettingsUseCaseOutput.Setting, ...]:
    return (
        _item(
            "scheduler_round_seconds",
            "Round interval",
            settings.round_seconds,
            _SECONDS,
            "How often a compaction round decides which partitions to compact next.",
        ),
        _item(
            "scheduler_budget_gb_hours",
            "Round budget",
            settings.budget_gb_hours,
            "GB·hours",
            "The most estimated compute a single round may grant, in GB·hours.",
        ),
        *[_priority_weight(priority) for priority in settings.priorities],
        *[_priority_sla(priority) for priority in settings.priorities],
        _item(
            "scheduler_grant_lease_seconds",
            "Grant retention",
            settings.grant_lease_seconds,
            _SECONDS,
            "How long a granted partition stays reserved for its table to claim before the grant lapses.",
        ),
        _item(
            "compaction_partitions_per_run",
            "Partitions per run",
            settings.partitions_per_run,
            "partitions",
            "The most partitions one compaction run rewrites.",
        ),
        _item(
            "compaction_quiet_seconds",
            "Quiet period",
            settings.quiet_seconds,
            _SECONDS,
            "How long a partition must go without a new write before it is compacted.",
        ),
        _item(
            "compaction_max_quiet_wait_seconds",
            "Longest quiet wait",
            settings.max_quiet_wait_seconds,
            _SECONDS,
            "The longest a partition that keeps receiving writes is held back before it is compacted anyway.",
        ),
        _item(
            "compaction_min_partition_bytes",
            "Minimum partition size",
            settings.min_partition_bytes,
            "bytes",
            "A partition with less data than this is left alone as too small to compact.",
        ),
    )


def _priority_weight(priority: PlatformPriority) -> GetPlatformSettingsUseCaseOutput.Setting:
    name = priority.priority
    return _item(
        f"scheduler_priority_weight_{name.lower()}",
        f"{name} weight",
        priority.weight,
        "times",
        f"How many times a {name} partition's score is multiplied when a round ranks partitions.",
    )


def _priority_sla(priority: PlatformPriority) -> GetPlatformSettingsUseCaseOutput.Setting:
    name = priority.priority
    return _item(
        f"scheduler_sla_seconds_{name.lower()}",
        f"{name} SLA",
        priority.sla_seconds,
        _SECONDS,
        f"How long a {name} partition may wait for compaction before it is shown as overdue.",
    )
