"""Test how translate_domain_errors maps domain errors to application exceptions."""

from __future__ import annotations

from datetime import timedelta

import pytest

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceSettings,
)
from context.table_maintenance.application.exceptions import (
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.service.shared import (
    translate_domain_errors,
)


def test_an_invalid_value_object_becomes_a_one_line_validation_error() -> None:
    """A broken invariant reads as one line naming the field."""
    with pytest.raises(ValidationError) as caught, translate_domain_errors():
        MaintenanceSettings.from_primitives({"remove_orphan_files": {"older_than_seconds": 60}})
    assert str(caught.value) == "remove_orphan_files.older_than_seconds: must be at least 1 day"


def test_an_invalid_construction_becomes_a_validation_error() -> None:
    """Building a value object with a broken invariant in code is a validation error too."""
    with pytest.raises(ValidationError) as caught, translate_domain_errors():
        MaintenanceSettings(reconcile_interval=timedelta(0))
    assert str(caught.value) == "reconcile_interval: must be positive"


def test_a_plain_value_error_keeps_its_message() -> None:
    """Any other ValueError becomes a ValidationError with the same message."""
    with pytest.raises(ValidationError, match="^bad value$"), translate_domain_errors():
        raise ValueError("bad value")


def test_a_lookup_error_becomes_not_found() -> None:
    """A repo LookupError becomes a NotFoundError."""
    with pytest.raises(NotFoundError, match="missing"), translate_domain_errors():
        raise LookupError("missing")
