"""Define the RunStatus base of the maintenance run's status classes."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, ClassVar

from context.table_maintenance.application.domain.model.table_maintenance_run.status.invalid_run_transition import (
    InvalidRunTransition,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status_name import (
        RunStatusName,
    )


class RunStatus(ABC):  # noqa: B024 - every move has a refusing default; a status overrides only the moves it allows
    """The status of a maintenance run, one class per status (State pattern).

    Each move returns the run's next status. Here every move is refused with ``InvalidRunTransition``; a status
    class overrides only the moves it allows. Each status class also extends ``ValueObject`` directly: it has no
    fields, so two statuses are equal exactly when they are of the same class.
    """

    name: ClassVar[RunStatusName]
    is_terminal: ClassVar[bool] = False
    is_in_flight: ClassVar[bool] = False

    def start_attempt(self) -> RunStatus:
        """Return the status once an attempt is submitted."""
        raise self._refused("start_attempt")

    def mark_running(self) -> RunStatus:
        """Return the status once the submitted attempt runs."""
        raise self._refused("mark_running")

    def succeed(self) -> RunStatus:
        """Return the status once the attempt succeeds."""
        raise self._refused("succeed")

    def fail(self, *, retries: bool) -> RunStatus:
        """Return the status once the attempt fails: waiting to retry when ``retries``, otherwise failed."""
        raise self._refused("fail")

    def cancel(self) -> RunStatus:
        """Return the status once the run is cancelled."""
        raise self._refused("cancel")

    def skip(self) -> RunStatus:
        """Return the status once the run is skipped without starting."""
        raise self._refused("skip")

    def _refused(self, action: str) -> InvalidRunTransition:
        """Return the refusal of the move named ``action`` from this status."""
        return InvalidRunTransition(f"cannot {action} a run that is {self.name}")
