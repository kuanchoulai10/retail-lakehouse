from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ExpireSnapshotsConfig(BaseModel):
    """
    Config for CALL <catalog>.system.expire_snapshots(...)

    Env vars (delimiter: __):
      EXPIRE_SNAPSHOTS__TABLE                  required
      EXPIRE_SNAPSHOTS__OLDER_THAN             optional ISO-8601 timestamp
      EXPIRE_SNAPSHOTS__RETAIN_LAST            optional int, default 1
      EXPIRE_SNAPSHOTS__MAX_CONCURRENT_DELETES optional int
      EXPIRE_SNAPSHOTS__STREAM_RESULTS         optional bool, default false
    """

    table: Optional[str] = None
    older_than: Optional[datetime] = None
    retain_last: int = 1
    max_concurrent_deletes: Optional[int] = None
    stream_results: bool = False

