class JobNotFoundError(Exception):
    """Raised when a job is not found in the repository."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Job {name!r} not found")
