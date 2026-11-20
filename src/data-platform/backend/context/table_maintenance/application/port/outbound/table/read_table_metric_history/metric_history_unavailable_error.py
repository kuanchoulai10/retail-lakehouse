"""Define the MetricHistoryUnavailableError."""

from __future__ import annotations


class MetricHistoryUnavailableError(Exception):
    """The metric history cannot be read: it is unreachable, answers with an error or answers nonsense.

    Raised instead of an empty history, so a caller can never mistake a failed read for a table that has no data.
    """

    def __init__(self, reason: str) -> None:
        """Remember why the history could not be read."""
        super().__init__(reason)
        self.reason = reason
