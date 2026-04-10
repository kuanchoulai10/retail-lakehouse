from repos import BaseJobsRepo


def get_repo() -> BaseJobsRepo:
    raise NotImplementedError("Dependency not wired — call app.dependency_overrides[get_repo]")
