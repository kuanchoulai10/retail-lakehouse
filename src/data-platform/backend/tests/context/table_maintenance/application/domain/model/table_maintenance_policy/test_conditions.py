"""Test the conditions value objects."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    AtLeast,
    RemoveOrphanFilesConditions,
    RewriteDataFilesConditions,
    RewriteManifestsConditions,
    SmallManifestsCondition,
)


def test_missing_condition_means_empty() -> None:
    """Check the behaviour named by the test."""
    assert RewriteDataFilesConditions().is_empty()
    assert not RewriteDataFilesConditions(reducible_files=AtLeast(at_least=1)).is_empty()
    assert RewriteManifestsConditions().is_empty()
    assert not RewriteManifestsConditions(small_manifests=SmallManifestsCondition(at_least=2)).is_empty()
    assert RemoveOrphanFilesConditions().is_empty()


def test_at_least_zero_is_rejected() -> None:
    """Check the behaviour named by the test."""
    with pytest.raises(ValidationError):
        AtLeast.from_primitives({"at_least": 0})
