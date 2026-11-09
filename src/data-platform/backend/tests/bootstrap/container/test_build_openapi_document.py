"""Test that the OpenAPI document is built from the real app without any running dependency."""

from __future__ import annotations

from bootstrap.container import build_openapi_document


def test_document_holds_both_contexts_routes():
    """The document is the full API: table maintenance and catalog routes, with their schemas."""
    document = build_openapi_document()

    assert document["info"]["title"] == "Data Platform API"
    assert {"/v1/table-maintenance-presets", "/v1/catalogs", "/v1/catalogs/{catalog}"} <= set(document["paths"])
    assert document["components"]["schemas"]


def test_document_is_independent_of_the_deployment_root_path(monkeypatch):
    """A root path set for the gateway does not leak into the document the console is generated from."""
    monkeypatch.setenv("GLAC_API__ROOT_PATH", "/api")

    document = build_openapi_document()

    assert "servers" not in document


def test_operation_ids_are_the_route_names_and_unique():
    """The generated console client names its hooks after these, so they are short and never collide across contexts."""
    document = build_openapi_document()

    ids = [operation["operationId"] for path in document["paths"].values() for operation in path.values()]

    assert len(ids) == len(set(ids))
    assert document["paths"]["/v1/catalogs"]["get"]["operationId"] == "list_catalogs"
    assert document["paths"]["/v1/tables"]["get"]["operationId"] == "list_tables"
    assert (
        document["paths"]["/v1/catalogs/{catalog}/namespaces/{namespace}/tables"]["get"]["operationId"]
        == "list_catalog_tables"
    )
