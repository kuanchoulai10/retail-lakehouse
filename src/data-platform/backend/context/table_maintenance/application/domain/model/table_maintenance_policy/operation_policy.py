"""Define the OperationPolicy value object."""

from __future__ import annotations

from base import ValueObject


class OperationPolicy[T: ValueObject, E: ValueObject](ValueObject):
    """Say whether an operation is enabled, when it is due and how it runs."""

    enabled: bool
    trigger_policy: T
    execution_policy: E
