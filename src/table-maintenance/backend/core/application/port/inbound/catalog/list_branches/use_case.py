"""Define the ListBranchesUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from core.application.port.inbound.catalog.list_branches.input import ListBranchesInput
from core.application.port.inbound.catalog.list_branches.output import (
    ListBranchesOutput,
)


class ListBranchesUseCase(UseCase[ListBranchesInput, ListBranchesOutput]):
    """List all branches for a table."""
