"""Tests for the size_for_bytes domain service."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import ComputeSize
from context.table_maintenance.application.domain.service.shared import size_for_bytes

MIB = 1024**2


@pytest.mark.parametrize(
    ("data_bytes", "size"),
    [
        (0, ComputeSize.S),
        (256 * MIB, ComputeSize.S),
        (256 * MIB + 1, ComputeSize.M),
        (1024 * MIB, ComputeSize.M),
        (1024 * MIB + 1, ComputeSize.L),
        (2048 * MIB, ComputeSize.L),
    ],
)
def test_size_follows_the_data_to_compact(data_bytes, size):
    """Up to the S bound is S, up to the M bound is M, anything more is L."""
    assert size_for_bytes(data_bytes, s_max_bytes=256 * MIB, m_max_bytes=1024 * MIB) is size
