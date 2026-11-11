"""Define the TriggerPolicy value object."""

from __future__ import annotations

from pydantic import Field

from base import ValueObject, WholeSeconds


class TriggerPolicy[C: ValueObject](ValueObject):
    """Decide when an operation is due: a cooldown between runs and its conditions."""

    cooldown: WholeSeconds = Field(
        validation_alias="cooldown_seconds",
        serialization_alias="cooldown_seconds",
    )
    conditions: C
