"""Define domain exceptions for the Job aggregate."""


class JobNotFoundError(Exception):
    """Raised when a job is not found in the repository."""

    def __init__(self, name: str) -> None:
        """Initialize with the name of the missing job."""
        self.name = name
        super().__init__(f"Job {name!r} not found")


class InvalidJobStateTransitionError(Exception):
    """Raised when a Job state transition is not allowed."""

    def __init__(self, current: str, target: str) -> None:
        """Initialize with the current and target states."""
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition job from {current!r} to {target!r}")


class JobNotActiveError(Exception):
    """Raised when a run is requested for a Job that is not active."""

    def __init__(self, job_id: str) -> None:
        """Initialize with the ID of the non-active job."""
        self.job_id = job_id
        super().__init__(
            f"Job {job_id!r} is not active — only active jobs can be triggered"
        )


class MaxActiveRunsExceededError(Exception):
    """Raised when a job has reached its max concurrent active runs."""

    def __init__(self, job_id: str, max_active_runs: int) -> None:
        """Initialize with the job ID and its max active runs limit."""
        self.job_id = job_id
        self.max_active_runs = max_active_runs
        super().__init__(f"Job {job_id!r} already has {max_active_runs} active run(s)")
