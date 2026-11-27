"""Define the ConcurrentUpdateError exception."""

from __future__ import annotations


class ConcurrentUpdateError(Exception):
    """Signal that a save was made from a stale copy: someone else changed the record since it was read.

    It is not a ``ConflictError``: reading the record again and redoing the change may succeed, so a
    retry is worth it.
    """
