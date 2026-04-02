from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Strategy(str, Enum):
    BINPACK = "binpack"
    SORT = "sort"
    ZORDER = "zorder"


class RewriteDataFilesConfig(BaseModel):
    """
    Config for CALL <catalog>.system.rewrite_data_files(...)

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

    table: Optional[str] = None
    strategy: Strategy = Strategy.BINPACK
    sort_order: Optional[str] = None
    where: Optional[str] = None
    # Iceberg options map entries
    target_file_size_bytes: Optional[int] = None
    min_file_size_bytes: Optional[int] = None
    max_file_size_bytes: Optional[int] = None
    min_input_files: Optional[int] = None
    rewrite_all: Optional[bool] = None
    max_concurrent_file_group_rewrites: Optional[int] = None
    partial_progress_enabled: Optional[bool] = None
    partial_progress_max_commits: Optional[int] = None

