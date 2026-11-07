"""Define the register_error_handlers function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import status
from fastapi.responses import JSONResponse

from context.catalog.application.exceptions import (
    CatalogUnavailableError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    ValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    CatalogUnavailableError: status.HTTP_502_BAD_GATEWAY,
}


def register_error_handlers(app: FastAPI) -> None:
    """Map the catalog application exceptions to HTTP errors with a detail body."""
    for error_type, status_code in _STATUS_BY_ERROR.items():

        def handler(_request: Request, exc: Exception, status_code: int = status_code) -> JSONResponse:
            return JSONResponse(status_code=status_code, content={"detail": str(exc)})

        app.add_exception_handler(error_type, handler)
