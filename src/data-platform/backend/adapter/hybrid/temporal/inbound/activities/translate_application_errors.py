"""Define the translate_application_errors context manager."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from temporalio.exceptions import ApplicationError

from application.exceptions import ConflictError, NotFoundError, ValidationError

if TYPE_CHECKING:
    from collections.abc import Iterator

_NON_RETRYABLE = (ValidationError, NotFoundError, ConflictError)


@contextmanager
def translate_application_errors() -> Iterator[None]:
    """Turn application errors into non-retryable Temporal application errors.

    A validation, not-found or conflict error cannot succeed on retry, so it fails
    the activity at once with the exception class name as the error type. Any other
    exception propagates unchanged and stays retryable.
    """
    try:
        yield
    except _NON_RETRYABLE as error:
        raise ApplicationError(
            str(error), type=type(error).__name__, non_retryable=True
        ) from error
