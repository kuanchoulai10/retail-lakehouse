"""Define the CompactionRoundId identifier."""

from __future__ import annotations

from typing import ClassVar

from base import EntityId


class CompactionRoundId(EntityId):
    """Identify a CompactionRound; the round workflow mints it as a ``cr-`` id."""

    PREFIX: ClassVar[str | None] = "cr"
