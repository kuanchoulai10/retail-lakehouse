"""Provide remove_prefix, which removes a storage prefix a scenario wrote under."""

from __future__ import annotations

from pyarrow import fs


def remove_prefix(s3: fs.FileSystem, prefix: str) -> None:
    """Remove ``bucket/key`` with its directory marker, and fail when it is still there.

    ``delete_dir_contents`` would keep the marker, and ``delete_dir`` on S3 writes a marker for the
    parent directory, so a scenario removes each prefix it wrote under, deepest first.
    """
    if s3.get_file_info(prefix).type != fs.FileType.NotFound:
        s3.delete_dir(prefix)
    assert s3.get_file_info(prefix).type == fs.FileType.NotFound, f"{prefix} is still there after its removal"
