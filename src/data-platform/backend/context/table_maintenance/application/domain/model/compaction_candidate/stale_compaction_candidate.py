"""Define the StaleCompactionCandidate exception."""

from __future__ import annotations


class StaleCompactionCandidate(Exception):
    """Raise when a candidate is saved from a version another writer has moved past.

    Nothing of that save is stored. It is not a ``ValueError``: the caller is
    expected to read the candidates again and retry, not to report bad input.
    """
