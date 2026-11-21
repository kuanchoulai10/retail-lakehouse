"""Define the GetEffectivePoliciesUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetEffectivePoliciesUseCaseInput(UseCaseInput):
    """Carry the place to answer for: a table table maintenance records, or a place in the catalog.

    A ``table_uuid`` without ``catalog`` names a recorded table, placed by its recorded name. Otherwise
    ``catalog``, a dot-joined ``namespace`` in it and a ``table`` in that namespace name the place by
    location; a table named so need not be recorded.
    """

    catalog: str | None = None
    namespace: str | None = None
    table: str | None = None
    table_uuid: str | None = None
