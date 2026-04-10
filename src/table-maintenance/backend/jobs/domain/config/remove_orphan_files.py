from datetime import datetime

from pydantic import BaseModel


class RemoveOrphanFilesConfig(BaseModel):
    table: str | None = None
    older_than: datetime | None = None
    location: str | None = None
    dry_run: bool = False
    max_concurrent_deletes: int | None = None
