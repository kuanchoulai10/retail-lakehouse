"""Define the RewriteManifestsJob."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RewriteManifestsJob:
    """Describe a manifest rewrite; an option left ``None`` is the procedure's default."""

    use_caching: bool | None = None
