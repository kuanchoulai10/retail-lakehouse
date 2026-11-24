"""Provide append_retrying, an append that tries again on a fresh load when another commit beat it."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyiceberg.exceptions import CommitFailedException

if TYPE_CHECKING:
    from collections.abc import Callable

    import pyarrow as pa
    from pyiceberg.table import Table


def append_retrying(load: Callable[[], Table], rows: pa.Table, *, attempts: int = 5) -> int:
    """Append ``rows`` to the table ``load`` returns, loading it again after each lost commit race.

    PyIceberg does not retry an append whose commit finds the branch moved, as Iceberg's Java
    writers do; a writer that runs beside maintenance meets that whenever a compaction commits
    while it writes. Only ``CommitFailedException`` is retried, at most ``attempts`` tries, and
    the last one is raised. Returns how many tries the append took.
    """
    for attempt in range(1, attempts + 1):
        try:
            load().append(rows)
        except CommitFailedException:
            if attempt == attempts:
                raise
        else:
            return attempt
    raise AssertionError("unreachable")
