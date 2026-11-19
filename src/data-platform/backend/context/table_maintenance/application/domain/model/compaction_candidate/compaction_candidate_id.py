"""Define the CompactionCandidateId identifier."""

from __future__ import annotations

from typing import ClassVar

from base import EntityId


class CompactionCandidateId(EntityId):
    """Identify a CompactionCandidate: a ``cc-`` id minted when its partition is first found to need compaction.

    The id is random, not derived from the partition; the store keeps one
    candidate per table and partition, so a partition observed again keeps the
    candidate (and the id) it already has.
    """

    PREFIX: ClassVar[str | None] = "cc"
