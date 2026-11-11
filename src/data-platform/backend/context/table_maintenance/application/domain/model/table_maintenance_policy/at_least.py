"""Define the AtLeast value object."""

from __future__ import annotations

from pydantic import PositiveInt

from base import ValueObject


class AtLeast(ValueObject):
    """A threshold: the condition holds when the measured count reaches ``at_least``."""

    at_least: PositiveInt
