"""Define the fits_smaller_size domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from context.table_maintenance.application.domain.model.shared import ComputeSize, SizeMemory
    from context.table_maintenance.application.domain.model.table import PeakMemoryUse

FIT_MARGIN_PERCENT = 70


def fits_smaller_size(size: ComputeSize, peak: PeakMemoryUse, memory: Mapping[ComputeSize, SizeMemory]) -> bool:
    """Return whether a job that peaked at ``peak`` while running at ``size`` would fit the next smaller size.

    It fits when the coordinator's and the worker's peaks are both measured and both at most
    ``FIT_MARGIN_PERCENT`` of the heap the smaller size gives that role. The sizes do not halve
    from one to the next, so the peak is compared with the smaller size, never with a share of
    the size the job ran at.
    """
    smaller = size.smaller()
    smaller_memory = memory.get(smaller) if smaller is not None else None
    if smaller_memory is None or peak.coordinator_bytes is None or peak.worker_bytes is None:
        return False
    return (
        peak.coordinator_bytes * 100 <= smaller_memory.coordinator_bytes * FIT_MARGIN_PERCENT
        and peak.worker_bytes * 100 <= smaller_memory.worker_bytes * FIT_MARGIN_PERCENT
    )
