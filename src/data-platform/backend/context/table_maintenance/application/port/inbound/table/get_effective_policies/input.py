"""Define the GetEffectivePoliciesUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetEffectivePoliciesUseCaseInput(UseCaseInput):
    """Carry the place to answer for: a table table maintenance records, or a place in the catalog.

    A place is named either way, never both: a ``table_uuid`` alone names a recorded table, placed by its
    recorded name; ``catalog``, a dot-joined ``namespace`` in it and a ``table`` in that namespace name it
    by location, and a table named so need not be recorded.
    """

    catalog: str | None = None
    namespace: str | None = None
    table: str | None = None
    table_uuid: str | None = None
