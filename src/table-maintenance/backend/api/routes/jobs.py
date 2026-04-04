from fastapi import APIRouter, Depends, Response
from k8s.jobs_repo import JobsRepository
from models.requests import JobRequest
from models.responses import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_repo() -> JobsRepository:
    raise NotImplementedError("Dependency not wired — call app.dependency_overrides[get_repo]")


@router.post("", response_model=JobResponse, status_code=201)
def create_job(request: JobRequest, repo: JobsRepository = Depends(get_repo)):
    return repo.create(request)


@router.get("", response_model=list[JobResponse])
def list_jobs(repo: JobsRepository = Depends(get_repo)):
    return repo.list_all()


@router.get("/{name}", response_model=JobResponse)
def get_job(name: str, repo: JobsRepository = Depends(get_repo)):
    return repo.get(name)


@router.delete("/{name}", status_code=204, response_class=Response)
def delete_job(name: str, repo: JobsRepository = Depends(get_repo)):
    repo.delete(name)
