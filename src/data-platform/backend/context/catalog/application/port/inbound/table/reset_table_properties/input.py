"""Define the ResetTablePropertiesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResetTablePropertiesUseCaseInput:
    """Carry the keys to reset to default and the loaded uuid.

    ``expected_uuid`` is the uuid of the table as it was loaded; the reset is refused when the
    table under this name is no longer that table. A custom key is deleted.
    """

    catalog: str
    namespace: list[str]
    name: str
    expected_uuid: str
    keys: list[str]
