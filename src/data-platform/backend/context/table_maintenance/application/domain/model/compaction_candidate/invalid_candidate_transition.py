"""Define the InvalidCandidateTransition exception."""

from __future__ import annotations


class InvalidCandidateTransition(ValueError):
    """Raise when a compaction candidate command is not allowed in its current state."""
