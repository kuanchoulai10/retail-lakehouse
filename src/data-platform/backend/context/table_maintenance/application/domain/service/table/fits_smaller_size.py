"""Define the fits_smaller_size domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from context.table_maintenance.application.domain.model.shared import ComputeSize, SizeMemory
    from context.table_maintenance.application.domain.model.table import PeakHeapUse

FIT_MARGIN_PERCENT = 70


def fits_smaller_size(size: ComputeSize, peak: PeakHeapUse, memory: Mapping[ComputeSize, SizeMemory]) -> bool:
    """Return whether a job that peaked at ``peak`` while running at ``size`` would fit the next smaller size.

    It fits when the driver's and the executor's peaks are both measured and both at most
    ``FIT_MARGIN_PERCENT`` of the heap the smaller size gives that role. The sizes do not halve
    from one to the next, so the peak is compared with the smaller size, never with a share of
    the size the job ran at.
    """
    smaller = size.smaller()
    smaller_memory = memory.get(smaller) if smaller is not None else None
    if smaller_memory is None or peak.driver_bytes is None or peak.executor_bytes is None:
        return False
    return (
        peak.driver_bytes * 100 <= smaller_memory.driver_bytes * FIT_MARGIN_PERCENT
        and peak.executor_bytes * 100 <= smaller_memory.executor_bytes * FIT_MARGIN_PERCENT
    )
