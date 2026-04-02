from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RemoveOrphanFilesConfig(BaseModel):
    """
    Config for CALL <catalog>.system.remove_orphan_files(...)

    Env vars (delimiter: __):
      REMOVE_ORPHAN_FILES__TABLE                   required
      REMOVE_ORPHAN_FILES__OLDER_THAN              optional ISO-8601 timestamp (Iceberg default: 3 days ago)
      REMOVE_ORPHAN_FILES__LOCATION                optional, override scan location
      REMOVE_ORPHAN_FILES__DRY_RUN                 optional bool, default false
      REMOVE_ORPHAN_FILES__MAX_CONCURRENT_DELETES  optional int
    """

    table: Optional[str] = None
    older_than: Optional[datetime] = None
    location: Optional[str] = None
    dry_run: bool = False
    max_concurrent_deletes: Optional[int] = None

