from datetime import datetime

from pydantic import BaseModel


class ExpireSnapshotsConfig(BaseModel):
    table: str | None = None
    older_than: datetime | None = None
    retain_last: int = 1
    max_concurrent_deletes: int | None = None
    stream_results: bool = False
