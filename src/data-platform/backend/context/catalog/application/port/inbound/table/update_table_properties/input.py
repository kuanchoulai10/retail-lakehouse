"""Define the UpdateTablePropertiesUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class UpdateTablePropertiesUseCaseInput(UseCaseInput):
    """Carry the properties to set (``updates``), the keys to remove (``removals``) and the loaded uuid.

    ``expected_uuid`` is the uuid of the table as it was loaded; the save is refused when the
    table under this name is no longer that table.
    """

    catalog: str
    namespace: tuple[str, ...]
    name: str
    expected_uuid: str
    updates: dict[str, str] = {}
    removals: tuple[str, ...] = ()
