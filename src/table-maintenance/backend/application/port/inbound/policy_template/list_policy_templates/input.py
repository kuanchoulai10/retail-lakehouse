"""Define the ListPolicyTemplatesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListPolicyTemplatesUseCaseInput:
    """Carry the request to list all policy templates."""
