"""Fixtures every e2e scenario shares: settings, clients for the platform's services, and cleanup."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import httpx
import pytest
from pyarrow import fs
from temporalio.client import Client

from e2e.support import (
    CleanupStack,
    E2eSettings,
    OwnedCatalog,
    OwnedNames,
    PlatformApi,
    PolarisClient,
    TemporalSession,
    interrupt_on_sigterm,
    load_iceberg,
    misfiled_scenarios,
    sweep_leftovers,
    unique_suffix,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pyiceberg.catalog import Catalog


def pytest_configure(config: pytest.Config) -> None:
    """Register the two scenario kinds and refuse any other marker."""
    config.addinivalue_line("markers", "critical: a scenario that finishes in minutes, for pre-merge")
    config.addinivalue_line("markers", "full: a scenario of the full round, for nightly")
    config.option.strict_markers = True
    interrupt_on_sigterm()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Refuse a scenario that is not exactly one kind: an unmarked one would never run."""
    problems = misfiled_scenarios((item.nodeid, {marker.name for marker in item.iter_markers()}) for item in items)
    if problems:
        raise pytest.UsageError("every e2e scenario is marked critical or full:\n" + "\n".join(problems))


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
    return load_iceberg(settings, settings.catalog)


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


@pytest.fixture(scope="session", autouse=True)
def leftovers(
    request: pytest.FixtureRequest,
    settings: E2eSettings,
    platform: PlatformApi,
    iceberg: Catalog,
    s3: fs.S3FileSystem,
    polaris: PolarisClient,
    temporal: TemporalSession[Client],
) -> list[str]:
    """Remove what an earlier run that was cut short left, before any scenario starts."""
    removed = sweep_leftovers(
        platform=platform, iceberg=iceberg, s3=s3, polaris=polaris, temporal=temporal, catalog=settings.catalog
    )
    capture = request.config.pluginmanager.getplugin("capturemanager")
    with capture.global_and_fixture_disabled():
        for line in removed:
            print(f"removed what an earlier run left: {line}")  # noqa: T201 - the run's log says what it removed
    return removed


def _undo(stack: CleanupStack) -> None:
    errors = stack.run()
    if errors:
        pytest.fail("cleanup failed:\n" + "\n".join(errors), pytrace=False)


@pytest.fixture
def cleanup() -> Iterator[CleanupStack]:
    """Undo what the scenario created, newest first, whether it passed or failed."""
    stack = CleanupStack()
    yield stack
    _undo(stack)


@pytest.fixture(scope="module")
def module_cleanup() -> Iterator[CleanupStack]:
    """Undo what a module's shared setup created, after its last scenario."""
    stack = CleanupStack()
    yield stack
    _undo(stack)


@pytest.fixture(scope="module")
def owned_catalog(
    request: pytest.FixtureRequest,
    settings: E2eSettings,
    platform: PlatformApi,
    polaris: PolarisClient,
    s3: fs.S3FileSystem,
    suffix: str,
    module_cleanup: CleanupStack,
) -> OwnedCatalog:
    """Give the module a catalog of its own, named after the module, dropped after its last scenario."""
    scenario = request.module.__name__.rsplit(".", 1)[-1].removeprefix("test_")
    return OwnedCatalog.create(
        platform=platform,
        polaris=polaris,
        s3=s3,
        cleanup=module_cleanup,
        platform_catalog=settings.catalog,
        name=OwnedNames.catalog(suffix, scenario),
        load_iceberg=lambda warehouse: load_iceberg(settings, warehouse),
    )
