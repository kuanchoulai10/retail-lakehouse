"""Define the GetCompactionRoundUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.compaction_round.get_compaction_round.input import (
    GetCompactionRoundUseCaseInput,
)
from context.table_maintenance.application.port.inbound.compaction_round.get_compaction_round.output import (
    GetCompactionRoundUseCaseOutput,
)


class GetCompactionRoundUseCase(UseCase[GetCompactionRoundUseCaseInput, GetCompactionRoundUseCaseOutput]):
    """Read one recorded compaction round; an unknown round is not found."""

    @abstractmethod
    def execute(self, request: GetCompactionRoundUseCaseInput) -> GetCompactionRoundUseCaseOutput:
        """Read one recorded compaction round; an unknown round is not found."""
