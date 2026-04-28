"""Define the ListBranchesUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.catalog.list_branches.input import (
    ListBranchesUseCaseInput,
)
from application.port.inbound.catalog.list_branches.output import (
    ListBranchesUseCaseOutput,
)


class ListBranchesUseCase(UseCase[ListBranchesUseCaseInput, ListBranchesUseCaseOutput]):
    """List all branches for a table."""
