"""Test the translation of application errors into Temporal application errors."""

from __future__ import annotations

import pytest
from temporalio.exceptions import ApplicationError

from base import InvariantViolation, UseCaseInput
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    translate_application_errors,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)


@pytest.mark.parametrize("error_type", [ValidationError, NotFoundError, ConflictError])
def test_application_errors_become_non_retryable(error_type: type[Exception]):
    """Each application error type becomes a non-retryable ApplicationError."""
    with pytest.raises(ApplicationError) as caught:
        with translate_application_errors():
            raise error_type("boom")
    assert caught.value.non_retryable is True
    assert caught.value.type == error_type.__name__
    assert caught.value.message == "boom"
    assert isinstance(caught.value.__cause__, error_type)


def test_other_errors_stay_retryable_and_untouched():
    """Other errors pass through unchanged and stay retryable."""
    with pytest.raises(RuntimeError, match="transient"):
        with translate_application_errors():
            raise RuntimeError("transient")


def test_no_error_passes_through():
    """Without an error the call returns its value."""
    with translate_application_errors():
        value = 1
    assert value == 1


class _ProbeUseCaseInput(UseCaseInput):
    """An input with one int field."""

    limit: int


def test_an_input_the_activity_cannot_build_is_non_retryable() -> None:
    """An InvariantViolation from building an input fails the activity at once, typed by its class name."""
    with pytest.raises(ApplicationError) as caught:
        with translate_application_errors():
            _ProbeUseCaseInput.from_primitives({"limit": "1"})
    assert caught.value.non_retryable is True
    assert caught.value.type == "InvariantViolation"
    assert caught.value.message.startswith("limit: ")
    assert isinstance(caught.value.__cause__, InvariantViolation)
