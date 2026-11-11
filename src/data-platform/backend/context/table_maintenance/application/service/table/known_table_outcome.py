"""Define the KnownTableOutcome result."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table import (
        TableManagementChange,
    )


@dataclass(frozen=True)
class KnownTableOutcome:
    """Say what discovering a known table again did to it.

    ``renamed`` tells whether its name changed, ``change`` whether the rules
    managed or unmanaged it, and ``signalled`` whether the runtime was told of a
    table whose management did not change.
    """

    renamed: bool
    change: TableManagementChange
    signalled: bool
