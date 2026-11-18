"""Define the ResetTablePropertiesUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ResetTablePropertiesUseCaseInput(UseCaseInput):
    """Carry the keys to reset to default and the loaded uuid.

    ``expected_uuid`` is the uuid of the table as it was loaded; the reset is refused when the
    table under this name is no longer that table. A custom key is deleted.
    """

    catalog: str
    namespace: tuple[str, ...]
    name: str
    expected_uuid: str
    keys: tuple[str, ...]
