"""Define the ConnectionType enumeration."""

from __future__ import annotations

from enum import StrEnum


class ConnectionType(StrEnum):
    """Name the kind of remote catalog service an external catalog connects to.

    REST is a catalog that speaks the Iceberg REST protocol; HADOOP and HIVE are those catalogs.
    """

    REST = "REST"
    HADOOP = "HADOOP"
    HIVE = "HIVE"
