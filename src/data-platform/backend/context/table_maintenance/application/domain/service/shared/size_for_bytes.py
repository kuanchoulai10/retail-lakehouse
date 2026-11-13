"""Define the size_for_bytes domain service."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import ComputeSize


def size_for_bytes(data_bytes: int, *, s_max_bytes: int, m_max_bytes: int) -> ComputeSize:
    """Return the compute size that fits compacting ``data_bytes``: S up to ``s_max_bytes``, M up to ``m_max_bytes``."""
    if data_bytes <= s_max_bytes:
        return ComputeSize.S
    if data_bytes <= m_max_bytes:
        return ComputeSize.M
    return ComputeSize.L
