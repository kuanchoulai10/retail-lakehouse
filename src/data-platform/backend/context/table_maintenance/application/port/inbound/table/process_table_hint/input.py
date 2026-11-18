"""Define the ProcessTableHintUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ProcessTableHintUseCaseInput(UseCaseInput):
    """Carry the request to react to a catalog event hint about one table or namespace."""

    catalog: str
    namespace: str
    table: str | None
    event_type: str
