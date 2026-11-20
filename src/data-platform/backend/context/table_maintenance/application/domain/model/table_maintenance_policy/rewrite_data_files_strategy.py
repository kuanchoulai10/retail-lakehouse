"""Define the RewriteDataFilesStrategy enumeration."""

from __future__ import annotations

from enum import StrEnum


class RewriteDataFilesStrategy(StrEnum):
    """Enumerate the rewrite strategies of Iceberg's ``rewrite_data_files``."""

    BINPACK = "binpack"
    SORT = "sort"
