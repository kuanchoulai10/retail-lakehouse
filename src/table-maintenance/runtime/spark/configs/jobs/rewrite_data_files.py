"""Configure the rewrite_data_files maintenance procedure."""

from enum import StrEnum

from pydantic import BaseModel


class Strategy(StrEnum):
    """Enumerate the available rewrite strategies."""

    BINPACK = "binpack"
    SORT = "sort"
    ZORDER = "zorder"


class RewriteDataFilesConfig(BaseModel):
    """Configure the rewrite_data_files procedure call.

    Env vars (delimiter: __):
      REWRITE_DATA_FILES__TABLE                           required
      REWRITE_DATA_FILES__STRATEGY                        optional binpack|sort|zorder, default binpack
      REWRITE_DATA_FILES__SORT_ORDER                      optional sort order expression
      REWRITE_DATA_FILES__WHERE                           optional filter predicate
      REWRITE_DATA_FILES__TARGET_FILE_SIZE_BYTES          optional int (Iceberg default: 512 MB)
      REWRITE_DATA_FILES__MIN_FILE_SIZE_BYTES             optional int
      REWRITE_DATA_FILES__MAX_FILE_SIZE_BYTES             optional int
      REWRITE_DATA_FILES__MIN_INPUT_FILES                 optional int (Iceberg default: 5)
      REWRITE_DATA_FILES__REWRITE_ALL                     optional bool (Iceberg default: false)
      REWRITE_DATA_FILES__MAX_CONCURRENT_FILE_GROUP_REWRITES optional int (Iceberg default: 1)
      REWRITE_DATA_FILES__PARTIAL_PROGRESS_ENABLED        optional bool (Iceberg default: false)
      REWRITE_DATA_FILES__PARTIAL_PROGRESS_MAX_COMMITS    optional int (Iceberg default: 10)
    """

    table: str | None = None
    strategy: Strategy = Strategy.BINPACK
    sort_order: str | None = None
    where: str | None = None
    # Iceberg options map entries
    target_file_size_bytes: int | None = None
    min_file_size_bytes: int | None = None
    max_file_size_bytes: int | None = None
    min_input_files: int | None = None
    rewrite_all: bool | None = None
    max_concurrent_file_group_rewrites: int | None = None
    partial_progress_enabled: bool | None = None
    partial_progress_max_commits: int | None = None
