from fastapi import APIRouter, Depends, HTTPException, Response

from jobs.application.exceptions import JobNotFoundError
from jobs.application.port.inbound import DeleteJobInput, DeleteJobUseCase

router = APIRouter()


def _get_use_case() -> DeleteJobUseCase:
    raise NotImplementedError("Dependency not wired — call app.dependency_overrides")


@router.delete("/jobs/{name}", status_code=204, response_class=Response)
def delete_job(name: str, use_case: DeleteJobUseCase = Depends(_get_use_case)):
    try:
        use_case.execute(DeleteJobInput(job_id=name))
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
