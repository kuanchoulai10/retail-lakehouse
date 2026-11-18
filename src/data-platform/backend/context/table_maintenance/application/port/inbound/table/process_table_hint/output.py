"""Define the ProcessTableHintUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class ProcessTableHintUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to react to a catalog event hint about one table or namespace."""

    action: str
