"""Define the UpdateTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from typing import Any

from base import UseCaseInput


class UpdateTableMaintenancePolicyUseCaseInput(UseCaseInput):
    """Carry the request to replace a table maintenance policy's content as a new version."""

    name: str
    content: dict[str, Any]
    version: int
