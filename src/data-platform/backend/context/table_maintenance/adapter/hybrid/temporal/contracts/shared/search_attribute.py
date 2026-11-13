"""Define the names of the search attributes that tag table workflows."""

from __future__ import annotations

from enum import StrEnum


class TableSearchAttribute(StrEnum):
    """Name the search attributes that tag workflows with the tables they concern.

    Every reconciliation and maintenance workflow carries the first four; a
    compaction round carries ``GrantedTableUuids``, the tables it granted
    compaction to. The names are registered on the Temporal namespace by the Temporal wave, so
    they must never change: the console and operators find a table's workflows by them.
    """

    TABLE_UUID = "TableUuid"
    TABLE_NAME = "TableName"
    MAINTENANCE_OPERATIONS = "MaintenanceOperations"
    MAINTENANCE_TRIGGER = "MaintenanceTrigger"
    GRANTED_TABLE_UUIDS = "GrantedTableUuids"
