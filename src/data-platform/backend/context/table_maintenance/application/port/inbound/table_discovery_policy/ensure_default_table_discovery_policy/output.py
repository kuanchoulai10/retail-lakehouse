"""Define the EnsureDefaultTableDiscoveryPolicyUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class EnsureDefaultTableDiscoveryPolicyUseCaseOutput(UseCaseOutput):
    """Say whether the default was created now (True) or was already there (False)."""

    created: bool
