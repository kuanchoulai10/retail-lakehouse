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
        """Return the four groups of settings in the order the console shows them."""
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
                    key="cooldown_and_backoff",
                    title="Cooldown and backoff",
                    items=(
                        *_cooldowns(settings),
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


def _cooldown(key: str, label: str, seconds: int, operation: str) -> GetPlatformSettingsUseCaseOutput.Setting:
    return _item(key, label, seconds, _SECONDS, f"The least time between two runs of {operation} on one table.")


def _cooldowns(settings: PlatformSettings) -> tuple[GetPlatformSettingsUseCaseOutput.Setting, ...]:
    return (
        _cooldown(
            "maintenance_rewrite_data_files_cooldown_seconds",
            "Rewrite data files cooldown",
            settings.rewrite_data_files_cooldown_seconds,
            "rewrite data files",
        ),
        _cooldown(
            "maintenance_rewrite_manifests_cooldown_seconds",
            "Rewrite manifests cooldown",
            settings.rewrite_manifests_cooldown_seconds,
            "rewrite manifests",
        ),
        _cooldown(
            "maintenance_expire_snapshots_cooldown_seconds",
            "Expire snapshots cooldown",
            settings.expire_snapshots_cooldown_seconds,
            "expire snapshots",
        ),
        _item(
            "maintenance_remove_orphan_files_interval_seconds",
            "Orphan file removal interval",
            settings.remove_orphan_files_interval_seconds,
            _SECONDS,
            "How often orphan files are removed from a table: they have no target the platform can measure.",
        ),
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
