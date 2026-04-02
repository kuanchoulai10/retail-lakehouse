from enum import Enum


class JobType(str, Enum):
    EXPIRE_SNAPSHOTS = "expire_snapshots"
    REMOVE_ORPHAN_FILES = "remove_orphan_files"
    REWRITE_DATA_FILES = "rewrite_data_files"
    REWRITE_MANIFESTS = "rewrite_manifests"
