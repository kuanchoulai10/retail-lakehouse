"""Test how translate_domain_errors maps domain errors to application exceptions."""

from __future__ import annotations

from datetime import timedelta

import pytest

from base import UseCaseOutput
from context.table_maintenance.application.domain.model.table_discovery_policy import StaleDiscoveryPolicyVersion
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    RemoveOrphanFilesTarget,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.service.shared import (
    translate_domain_errors,
)


def test_an_invalid_value_object_becomes_a_one_line_validation_error() -> None:
    """A broken invariant reads as one line naming the field."""
    with pytest.raises(ValidationError) as caught, translate_domain_errors():
        RemoveOrphanFilesTarget.from_primitives({"older_than_seconds": 60})
    assert str(caught.value) == "older_than_seconds: must be at least 1 day"


def test_an_invalid_construction_becomes_a_validation_error() -> None:
    """Building a value object with a broken invariant in code is a validation error too."""
    with pytest.raises(ValidationError) as caught, translate_domain_errors():
        RemoveOrphanFilesTarget(older_than=timedelta(0))
    assert str(caught.value) == "older_than: must be at least 1 day"


def test_a_plain_value_error_keeps_its_message() -> None:
    """Any other ValueError becomes a ValidationError with the same message."""
    with pytest.raises(ValidationError, match="^bad value$"), translate_domain_errors():
        raise ValueError("bad value")


def test_a_stale_discovery_policy_version_becomes_a_conflict_error() -> None:
    """A stale discovery policy version is a conflict."""
    with pytest.raises(ConflictError, match="^refused$"), translate_domain_errors():
        raise StaleDiscoveryPolicyVersion("refused")


def test_a_lookup_error_becomes_not_found() -> None:
    """A repo LookupError becomes a NotFoundError."""
    with pytest.raises(NotFoundError, match="missing"), translate_domain_errors():
        raise LookupError("missing")


class _ProbeUseCaseOutput(UseCaseOutput):
    """An output with one tuple field."""

    names: tuple[str, ...]


def test_an_output_the_service_cannot_build_is_not_a_validation_error() -> None:
    """A refused output is a server bug: its TypeError passes through, never becoming a 422 ValidationError."""
    with pytest.raises(TypeError, match="_ProbeUseCaseOutput was built with refused data"), translate_domain_errors():
        _ProbeUseCaseOutput(names=["a"])  # ty: ignore[invalid-argument-type]
