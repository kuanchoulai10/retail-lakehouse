"""Define the CreateTableMaintenanceRunsUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class CreateTableMaintenanceRunsUseCaseOutput(UseCaseOutput):
    """Carry the ids of the plan's runs, in plan order, every one of which now exists."""

    run_ids: tuple[str, ...]
