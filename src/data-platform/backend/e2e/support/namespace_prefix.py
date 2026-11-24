"""Provide namespace_prefix, which turns a namespace's location into the storage prefix its cleanup removes."""

from __future__ import annotations


def namespace_prefix(location: str, namespace: str) -> str:
    """Return ``bucket/key`` of ``location``, which must be the namespace's own directory under a bucket.

    The cleanup removes this prefix recursively with the platform's storage key, so a location that
    is not ``.../<namespace>`` (a wider directory, the bucket itself) is refused instead of removed.
    """
    prefix = location.removeprefix("s3://").rstrip("/")
    bucket, _, key = prefix.partition("/")
    assert bucket and (key == namespace or key.endswith(f"/{namespace}")), (
        f"{location} is not the namespace's own directory for {namespace}"
    )
    return prefix
