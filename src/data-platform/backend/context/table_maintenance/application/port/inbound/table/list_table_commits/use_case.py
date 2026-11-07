"""Define the ListTableCommitsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table.list_table_commits.input import (
    ListTableCommitsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.list_table_commits.output import (
    ListTableCommitsUseCaseOutput,
)


class ListTableCommitsUseCase(UseCase[ListTableCommitsUseCaseInput, ListTableCommitsUseCaseOutput]):
    """List the commits of one table, newest first."""

    @abstractmethod
    def execute(self, request: ListTableCommitsUseCaseInput) -> ListTableCommitsUseCaseOutput:
        """List the commits of one table."""
