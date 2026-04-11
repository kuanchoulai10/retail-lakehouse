from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RewriteManifestsConfig:
    table: str | None = None
    use_caching: bool = True
    spec_id: int | None = None
