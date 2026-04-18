"""Define domain exceptions for the Job aggregate."""


class JobNotFoundError(Exception):
    """Raised when a job is not found in the repository."""

    def __init__(self, name: str) -> None:
        """Initialize with the name of the missing job."""
        self.name = name
        super().__init__(f"Job {name!r} not found")
