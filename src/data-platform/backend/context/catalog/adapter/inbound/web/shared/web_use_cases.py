"""Define the WebUseCases bundle."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebUseCases:
    """Hold every catalog use case the web API calls; the composition root builds it."""
