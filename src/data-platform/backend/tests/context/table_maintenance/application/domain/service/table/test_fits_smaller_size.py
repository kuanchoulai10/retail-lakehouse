"""Test whether a measured peak heap use would fit the next smaller size."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import ComputeSize, SizeMemory
from context.table_maintenance.application.domain.model.table import PeakHeapUse
from context.table_maintenance.application.domain.service.table import fits_smaller_size

MIB = 1024 * 1024
MEMORY = {
    ComputeSize.S: SizeMemory(driver_bytes=768 * MIB, executor_bytes=768 * MIB),
    ComputeSize.M: SizeMemory(driver_bytes=1024 * MIB, executor_bytes=1536 * MIB),
    ComputeSize.L: SizeMemory(driver_bytes=1536 * MIB, executor_bytes=2048 * MIB),
}


def _peak(driver_mib: int | None, executor_mib: int | None) -> PeakHeapUse:
    return PeakHeapUse(
        driver_bytes=None if driver_mib is None else driver_mib * MIB,
        executor_bytes=None if executor_mib is None else executor_mib * MIB,
    )


def test_a_job_that_needs_most_of_s_does_not_fit_s_from_m():
    """Half of M's executor heap is nearly all of S's, so a 700 MiB job at M stays at M."""
    assert fits_smaller_size(ComputeSize.M, _peak(300, 700), MEMORY) is False
    assert fits_smaller_size(ComputeSize.M, _peak(300, 753), MEMORY) is False


def test_a_job_well_inside_the_smaller_size_fits_it():
    """Peaks under 70 % of the smaller size's heap, for driver and executor, fit it."""
    assert fits_smaller_size(ComputeSize.M, _peak(300, 400), MEMORY) is True
    assert fits_smaller_size(ComputeSize.L, _peak(500, 1000), MEMORY) is True


def test_every_role_must_fit():
    """A driver that would not fit the smaller size keeps the size, however small the executor's peak."""
    assert fits_smaller_size(ComputeSize.M, _peak(600, 100), MEMORY) is False


def test_the_margin_is_seventy_percent_of_the_smaller_size():
    """A peak at 70 % of the smaller size fits; just above it does not."""
    at = int(768 * MIB * 0.7)
    assert fits_smaller_size(ComputeSize.M, PeakHeapUse(driver_bytes=at, executor_bytes=at), MEMORY) is True
    over = PeakHeapUse(driver_bytes=at, executor_bytes=at + MIB)
    assert fits_smaller_size(ComputeSize.M, over, MEMORY) is False


@pytest.mark.parametrize("peak", [_peak(None, 100), _peak(100, None), _peak(None, None)])
def test_an_unmeasured_role_does_not_fit(peak):
    """Without a peak for both roles nothing says the job would fit."""
    assert fits_smaller_size(ComputeSize.M, peak, MEMORY) is False


def test_nothing_fits_below_s():
    """S has no smaller size."""
    assert fits_smaller_size(ComputeSize.S, _peak(1, 1), MEMORY) is False


def test_an_unknown_smaller_size_does_not_fit():
    """Without the smaller size's memory nothing says the job would fit."""
    assert fits_smaller_size(ComputeSize.M, _peak(1, 1), {}) is False
