"""Define the DeletePolicyTemplateUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeletePolicyTemplateUseCaseOutput:
    """Signal completion; carries no data."""
