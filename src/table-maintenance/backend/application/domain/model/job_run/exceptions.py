"""Define domain exceptions for the JobRun aggregate."""


class JobRunNotFoundError(Exception):
    """Raised when a job run is not found in the repository."""

    def __init__(self, run_id: str) -> None:
        """Initialize with the ID of the missing job run."""
        self.run_id = run_id
        super().__init__(f"JobRun {run_id!r} not found")
