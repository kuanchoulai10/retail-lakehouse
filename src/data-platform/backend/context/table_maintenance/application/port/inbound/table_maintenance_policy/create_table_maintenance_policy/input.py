"""Define the CreateTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from typing import Any

from base import UseCaseInput


class CreateTableMaintenancePolicyUseCaseInput(UseCaseInput):
    """Carry the request to create a table maintenance policy at version 1."""

    name: str
    content: dict[str, Any]
