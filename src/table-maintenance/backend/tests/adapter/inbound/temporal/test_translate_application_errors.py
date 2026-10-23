"""Test the translation of application errors into Temporal application errors."""

from __future__ import annotations

import pytest
from temporalio.exceptions import ApplicationError

from adapter.inbound.temporal.activities.translate_application_errors import (
    translate_application_errors,
)
from application.exceptions import ConflictError, NotFoundError, ValidationError


@pytest.mark.parametrize("error_type", [ValidationError, NotFoundError, ConflictError])
def test_application_errors_become_non_retryable(error_type: type[Exception]):
    with pytest.raises(ApplicationError) as caught:
        with translate_application_errors():
            raise error_type("boom")
    assert caught.value.non_retryable is True
    assert caught.value.type == error_type.__name__
    assert caught.value.message == "boom"
    assert isinstance(caught.value.__cause__, error_type)


def test_other_errors_stay_retryable_and_untouched():
    with pytest.raises(RuntimeError, match="transient"):
        with translate_application_errors():
            raise RuntimeError("transient")


def test_no_error_passes_through():
    with translate_application_errors():
        value = 1
    assert value == 1
