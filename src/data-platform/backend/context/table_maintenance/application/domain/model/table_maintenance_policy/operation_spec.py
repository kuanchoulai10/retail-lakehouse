"""Define the OperationSpec value object."""

from __future__ import annotations

from base import ValueObject


class OperationSpec[T: ValueObject, O: ValueObject](ValueObject):
    """One operation of a policy: the target the table is kept at and the options the procedure runs with."""

    target: T
    options: O | None = None
