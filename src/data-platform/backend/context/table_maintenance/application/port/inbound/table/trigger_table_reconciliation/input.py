"""Define the TriggerTableReconciliationUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class TriggerTableReconciliationUseCaseInput(UseCaseInput):
    """Carry the request to reconcile a table now."""

    uuid: str
