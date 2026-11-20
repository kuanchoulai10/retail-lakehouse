"""Define the decide_next_attempt domain service."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import ComputeSize
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    FailureClass,
    NextAttempt,
    NextStep,
)

STOPPING_CLASSES = {
    FailureClass.CANCELLED: NextStep.CANCELLED,
    FailureClass.PERMANENT: NextStep.NOT_RETRIED,
    FailureClass.QUEUE_TIMEOUT: NextStep.NOT_RETRIED,
}


def decide_next_attempt(
    failure_class: FailureClass,
    size: ComputeSize | None,
    attempt: int,
    max_attempts: int,
    *,
    still_running: bool = False,
) -> NextAttempt:
    """Return what follows a failed attempt, from the first rule that holds.

    An attempt without a size started before sizes existed and ran at what is now S. An OOM at the
    largest size needs a person even when attempts remain, since a retry would hit the same wall. An
    attempt that waited in its queue past the limit is not retried: its operation waits for the next plan.
    """
    if still_running:
        return NextAttempt(step=NextStep.STILL_RUNNING)
    if failure_class in STOPPING_CLASSES:
        return NextAttempt(step=STOPPING_CLASSES[failure_class])
    current = size or ComputeSize.S
    larger = current.larger()
    if failure_class is FailureClass.OOM and larger is None:
        return NextAttempt(step=NextStep.NEEDS_ATTENTION)
    if attempt >= max_attempts:
        return NextAttempt(step=NextStep.ATTEMPTS_USED)
    if failure_class is FailureClass.OOM:
        return NextAttempt(step=NextStep.RETRY_LARGER, size=larger)
    return NextAttempt(step=NextStep.RETRY_SAME, size=current)
