class JobNotFoundError(Exception):
    """Application-layer exception: raised when a requested job does not exist."""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(f"Job {job_id!r} not found")


class JobRunNotFoundError(Exception):
    """Application-layer exception: raised when a requested job run does not exist."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"JobRun {run_id!r} not found")
