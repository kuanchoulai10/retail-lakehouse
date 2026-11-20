"""Define the MAX_SNAPSHOTS_TO_KEEP constant."""

from __future__ import annotations

MAX_SNAPSHOTS_TO_KEEP = 2147483647
"""The largest snapshot count Iceberg's ``retain_last`` takes: it is a Java ``int``."""
