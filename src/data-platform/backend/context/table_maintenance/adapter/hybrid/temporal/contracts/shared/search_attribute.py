"""Define the names of the search attributes that tag table workflows."""

from __future__ import annotations

from enum import StrEnum


class TableSearchAttribute(StrEnum):
    """Name the search attributes every reconciliation and maintenance workflow carries.

    The names are registered on the Temporal namespace by the Temporal wave, so
    they must never change: the console and operators find a table's workflows by them.
    """

    TABLE_UUID = "TableUuid"
    TABLE_NAME = "TableName"
    MAINTENANCE_OPERATIONS = "MaintenanceOperations"
    MAINTENANCE_TRIGGER = "MaintenanceTrigger"
