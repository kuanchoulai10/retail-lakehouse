"""Configure the remove_orphan_files maintenance procedure."""

from datetime import datetime

from pydantic import BaseModel


class RemoveOrphanFilesConfig(BaseModel):
    """Configure the remove_orphan_files procedure call.

    Env vars (delimiter: __):
      REMOVE_ORPHAN_FILES__TABLE                   required
      REMOVE_ORPHAN_FILES__OLDER_THAN              optional ISO-8601 timestamp (Iceberg default: 3 days ago)
      REMOVE_ORPHAN_FILES__LOCATION                optional, override scan location
      REMOVE_ORPHAN_FILES__DRY_RUN                 optional bool, default false
      REMOVE_ORPHAN_FILES__MAX_CONCURRENT_DELETES  optional int
    """

    table: str | None = None
    older_than: datetime | None = None
    location: str | None = None
    dry_run: bool = False
    max_concurrent_deletes: int | None = None
