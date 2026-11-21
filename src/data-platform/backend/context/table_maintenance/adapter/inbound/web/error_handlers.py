"""Define the register_error_handlers function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import status
from fastapi.responses import JSONResponse

from base import InvariantViolation
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.outbound.table import (
    CatalogAccessDeniedError,
    CatalogNotFoundError,
    MetricHistoryUnavailableError,
)

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    CatalogNotFoundError: status.HTTP_404_NOT_FOUND,
    CatalogAccessDeniedError: status.HTTP_403_FORBIDDEN,
    ConflictError: status.HTTP_409_CONFLICT,
    MetricHistoryUnavailableError: status.HTTP_502_BAD_GATEWAY,
    ValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InvariantViolation: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def register_error_handlers(app: FastAPI) -> None:
    """Map the application exceptions to HTTP errors with a detail body.

    A port input the router cannot build (``InvariantViolation``) is a client error, answered like ``ValidationError``.
    """
    for error_type, status_code in _STATUS_BY_ERROR.items():

        def handler(_request: Request, exc: Exception, status_code: int = status_code) -> JSONResponse:
            return JSONResponse(status_code=status_code, content={"detail": str(exc)})

        app.add_exception_handler(error_type, handler)
