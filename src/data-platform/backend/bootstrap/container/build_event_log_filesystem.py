"""Provide the build_event_log_filesystem function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyarrow.fs import S3FileSystem

if TYPE_CHECKING:
    from bootstrap.configs import AppSettings

HTTP_PREFIX = "http://"
HTTPS_PREFIX = "https://"


def build_event_log_filesystem(settings: AppSettings) -> S3FileSystem:
    """Return the object-store file system that holds the Spark event logs: the catalog's, path style.

    The catalog's S3 keys are used when they are set; otherwise the AWS environment chain
    supplies them (the worker gets them from its S3 Secret).
    """
    catalog = settings.catalog
    endpoint = catalog.s3_endpoint
    scheme = "http" if endpoint.startswith(HTTP_PREFIX) else "https"
    options: dict[str, Any] = {
        "endpoint_override": endpoint.removeprefix(HTTP_PREFIX).removeprefix(HTTPS_PREFIX).rstrip("/"),
        "scheme": scheme,
        "region": catalog.s3_region,
        "force_virtual_addressing": False,
    }
    if catalog.s3_access_key_id is not None and catalog.s3_secret_access_key is not None:
        options["access_key"] = catalog.s3_access_key_id.get_secret_value()
        options["secret_key"] = catalog.s3_secret_access_key.get_secret_value()
    return S3FileSystem(**options)
