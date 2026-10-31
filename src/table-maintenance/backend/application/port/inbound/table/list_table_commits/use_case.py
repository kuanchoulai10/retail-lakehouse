"""Define the ListTableCommitsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table.list_table_commits.input import (
    ListTableCommitsUseCaseInput,
)
from application.port.inbound.table.list_table_commits.output import (
    ListTableCommitsUseCaseOutput,
)
from base import UseCase


class ListTableCommitsUseCase(
    UseCase[ListTableCommitsUseCaseInput, ListTableCommitsUseCaseOutput]
):
    """List the commits of one table, newest first."""

    @abstractmethod
    def execute(
        self, request: ListTableCommitsUseCaseInput
    ) -> ListTableCommitsUseCaseOutput:
        """List the commits of one table."""
