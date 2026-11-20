"""Define the MissingTableSearchAttributes error."""

from __future__ import annotations


class MissingTableSearchAttributes(RuntimeError):
    """Raised at worker start when the namespace lacks a search attribute the workflows set.

    Temporal fails the workflow task of a workflow that upserts an unregistered
    attribute and retries it without end, so the worker refuses to start
    instead of letting every workflow that tags itself fail its workflow task.
    """
