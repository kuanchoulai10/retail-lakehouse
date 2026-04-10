from jobs.application.port.outbound.jobs_repo import BaseJobsRepo


def get_repo() -> BaseJobsRepo:
    raise NotImplementedError("Dependency not wired — call app.dependency_overrides[get_repo]")
