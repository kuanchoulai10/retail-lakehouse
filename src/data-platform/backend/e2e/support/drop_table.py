"""Provide drop_table, which drops a scenario's table and removes its storage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyiceberg.exceptions import NoSuchTableError

from e2e.support.remove_prefix import remove_prefix

if TYPE_CHECKING:
    from pyarrow import fs
    from pyiceberg.catalog import Catalog


def drop_table(iceberg: Catalog, s3: fs.FileSystem, identifier: tuple[str, str]) -> None:
    """Drop the table from the catalog, then remove its location (a table already gone is left alone)."""
    try:
        location = iceberg.load_table(identifier).location()
    except NoSuchTableError:
        return
    iceberg.drop_table(identifier)
    remove_prefix(s3, location.removeprefix("s3://").rstrip("/"))
