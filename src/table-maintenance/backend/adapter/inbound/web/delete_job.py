from __future__ import annotations

from dependencies.use_cases import get_delete_job_use_case
from fastapi import APIRouter, Depends, HTTPException, Response

from application.exceptions import JobNotFoundError
from application.port.inbound import DeleteJobInput, DeleteJobUseCase

router = APIRouter()


@router.delete("/jobs/{name}", status_code=204, response_class=Response)
def delete_job(
    name: str,
    use_case: DeleteJobUseCase = Depends(get_delete_job_use_case),
):
    try:
        use_case.execute(DeleteJobInput(job_id=name))
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
