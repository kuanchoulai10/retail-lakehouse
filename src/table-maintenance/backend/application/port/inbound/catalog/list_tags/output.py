"""Define the ListTagsUseCaseOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListTagsUseCaseOutputItem:
    """A single tag in the result."""

    name: str
    snapshot_id: int
    max_ref_age_ms: int | None


@dataclass(frozen=True)
class ListTagsUseCaseOutput:
    """Output for the ListTags use case."""

    tags: list[ListTagsUseCaseOutputItem]
