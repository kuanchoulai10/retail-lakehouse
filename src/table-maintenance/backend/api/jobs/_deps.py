from repos.jobs_repo import JobsRepo


def get_repo() -> JobsRepo:
    raise NotImplementedError("Dependency not wired — call app.dependency_overrides[get_repo]")
