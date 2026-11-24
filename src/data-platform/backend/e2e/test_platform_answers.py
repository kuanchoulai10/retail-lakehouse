"""The platform's services answer the e2e: the API, Polaris through PyIceberg, and Temporal."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from temporalio.api.workflowservice.v1 import DescribeNamespaceRequest

if TYPE_CHECKING:
    import httpx
    from pyiceberg.catalog import Catalog
    from temporalio.client import Client

    from e2e.support import E2eSettings, TemporalSession

pytestmark = pytest.mark.critical


def test_the_api_lists_the_catalog_and_its_namespaces(api: httpx.Client, settings: E2eSettings):
    """The table maintenance API knows the platform's catalog and can read its namespaces."""
    catalogs = api.get("/v1/catalogs")
    assert catalogs.status_code == 200, catalogs.text
    assert settings.catalog in [catalog["name"] for catalog in catalogs.json()]
    namespaces = api.get(f"/v1/catalogs/{settings.catalog}/namespaces")
    assert namespaces.status_code == 200, namespaces.text


def test_the_e2e_principal_reads_the_catalog_with_pyiceberg(iceberg: Catalog):
    """The e2e's own principal can list the catalog's namespaces through PyIceberg."""
    assert isinstance(iceberg.list_namespaces(), list)


def test_temporal_answers_for_the_platform_namespace(temporal: TemporalSession[Client], settings: E2eSettings):
    """Temporal describes the namespace the platform's workflows run in."""

    async def describe(client: Client) -> str:
        request = DescribeNamespaceRequest(namespace=settings.temporal_namespace)
        reply = await client.workflow_service.describe_namespace(request)
        return reply.namespace_info.name

    assert temporal.run(describe) == settings.temporal_namespace
