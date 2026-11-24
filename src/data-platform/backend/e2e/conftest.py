"""Fixtures every e2e scenario shares: settings, clients for the platform's services, and cleanup."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import httpx
import pytest
from pyarrow import fs
from pyiceberg.catalog import load_catalog
from temporalio.client import Client

from e2e.support import CleanupStack, E2eSettings, PlatformApi, PolarisClient, TemporalSession, unique_suffix

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pyiceberg.catalog import Catalog


def pytest_configure(config: pytest.Config) -> None:
    """Register the two scenario kinds and refuse any other marker."""
    config.addinivalue_line("markers", "critical: a scenario that finishes in minutes, for pre-merge")
    config.addinivalue_line("markers", "full: a scenario of the full round, for nightly")
    config.option.strict_markers = True


@pytest.fixture(scope="session")
def settings() -> E2eSettings:
    """Read where the platform is and the e2e's credentials from the pod's environment."""
    return E2eSettings.from_environment(os.environ)


@pytest.fixture(scope="session")
def suffix() -> str:
    """Return the suffix that makes this run's names its own."""
    return unique_suffix()


@pytest.fixture(scope="session")
def api(settings: E2eSettings) -> Iterator[httpx.Client]:
    """Call the table maintenance API."""
    with httpx.Client(base_url=settings.api_url, timeout=60) as client:
        yield client


@pytest.fixture(scope="session")
def platform(api: httpx.Client) -> PlatformApi:
    """Call the table maintenance API through the scenarios' client."""
    return PlatformApi(api)


@pytest.fixture(scope="session")
def polaris(settings: E2eSettings) -> Iterator[PolarisClient]:
    """Call Polaris as the e2e principal."""
    with httpx.Client() as http:
        yield PolarisClient(
            http,
            catalog_uri=settings.catalog_uri,
            management_uri=settings.management_uri,
            credential=settings.polaris_credential,
            scope=settings.scope,
        )


@pytest.fixture(scope="session")
def iceberg(settings: E2eSettings) -> Catalog:
    """Read and write the platform's catalog with PyIceberg as the e2e principal."""
    return load_catalog(
        "e2e",
        type="rest",
        uri=settings.catalog_uri,
        credential=settings.polaris_credential,
        warehouse=settings.catalog,
        scope=settings.scope,
        **{
            "oauth2-server-uri": f"{settings.catalog_uri}/v1/oauth/tokens",
            "s3.endpoint": settings.s3_endpoint,
            "s3.path-style-access": "true",
            "s3.region": settings.s3_region,
            "s3.access-key-id": settings.s3_access_key_id,
            "s3.secret-access-key": settings.s3_secret_access_key,
        },
    )


@pytest.fixture(scope="session")
def s3(settings: E2eSettings) -> fs.S3FileSystem:
    """List and remove objects on the platform's object storage."""
    scheme, _, endpoint = settings.s3_endpoint.partition("://")
    return fs.S3FileSystem(
        access_key=settings.s3_access_key_id,
        secret_key=settings.s3_secret_access_key,
        region=settings.s3_region,
        endpoint_override=endpoint,
        scheme=scheme,
        force_virtual_addressing=False,
        allow_bucket_creation=True,
    )


@pytest.fixture(scope="session")
def temporal(settings: E2eSettings) -> Iterator[TemporalSession[Client]]:
    """Describe the platform's workflows and schedules."""
    session = TemporalSession.connect(
        lambda: Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    )
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def cleanup() -> Iterator[CleanupStack]:
    """Undo what the scenario created, newest first, whether it passed or failed."""
    stack = CleanupStack()
    yield stack
    errors = stack.run()
    if errors:
        pytest.fail("cleanup failed:\n" + "\n".join(errors), pytrace=False)
