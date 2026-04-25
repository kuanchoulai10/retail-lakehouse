"""Define the ListTagsInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListTagsInput:
    """Input for the ListTags use case."""

    namespace: str
    table: str
