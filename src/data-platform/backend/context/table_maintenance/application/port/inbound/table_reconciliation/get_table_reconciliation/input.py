"""Define the GetTableReconciliationUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetTableReconciliationUseCaseInput(UseCaseInput):
    """Carry the request to get one reconciliation by its ``rc-`` id."""

    reconciliation_id: str
