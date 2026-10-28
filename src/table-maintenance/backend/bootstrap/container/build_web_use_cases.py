"""Provide the build_web_use_cases function."""

from __future__ import annotations

from dataclasses import fields
from typing import TYPE_CHECKING

from adapter.inbound.web import WebUseCases

if TYPE_CHECKING:
    from bootstrap.container.use_cases import UseCases


def build_web_use_cases(use_cases: UseCases) -> WebUseCases:
    """Select the use cases the web API calls; each field shares its service."""
    return WebUseCases(
        **{f.name: getattr(use_cases, f.name) for f in fields(WebUseCases)}
    )
