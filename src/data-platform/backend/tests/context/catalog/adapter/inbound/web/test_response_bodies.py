"""Test that the table, view, namespace and generic table bodies are byte for byte as before Pydantic.

Each request runs the real service over the real Polaris repo against a stubbed Polaris reply,
so the reply mapper, the domain model, the output mapping and the web response are all covered.
The expected text was captured from the code before the domain moved to Pydantic.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from context.catalog.adapter.outbound.generic_table.polaris import GenericTablesPolarisRepo
from context.catalog.adapter.outbound.namespace.polaris import NamespacesPolarisRepo
from context.catalog.adapter.outbound.table.polaris import TablesPolarisRepo
from context.catalog.adapter.outbound.view.polaris import ViewsPolarisRepo
from context.catalog.application.service.generic_table import GetGenericTableService
from context.catalog.application.service.namespace import GetNamespaceService
from context.catalog.application.service.table import GetTableService
from context.catalog.application.service.view import GetViewService
from tests.context.catalog.adapter.inbound.web.web_test_support import build_client
from tests.context.catalog.adapter.outbound.shared.polaris.polaris_stub import PolarisStub

OUTBOUND = Path(__file__).parents[2] / "outbound"
LOAD_TABLE = json.loads((OUTBOUND / "table" / "polaris" / "fixtures" / "load_table_result_v2.json").read_text())
LOAD_VIEW = json.loads((OUTBOUND / "view" / "polaris" / "fixtures" / "load_view_result.json").read_text())

TABLE_TEXT = (
    '{"catalog":"sales","namespace":["retail"],"name":"orders","uuid":"9c12d441-03fe-4693-9a96-a0705d'
    'df69c1","format_version":2,"location":"s3://lakehouse/iceberg/retail/orders","current_snapshot_i'
    'd":"3051729675574597004","last_updated_ms":1762516800123,"schema":{"schema_id":1,"fields":[{"id"'
    ':1,"name":"order_id","type":"long","required":true,"doc":"Primary key from MySQL"},{"id":2,"name'
    '":"customer_id","type":"long","required":false,"doc":null},{"id":3,"name":"order_ts","type":"tim'
    'estamptz","required":false,"doc":null},{"id":4,"name":"amount","type":"decimal(10,2)","required"'
    ':false,"doc":null},{"id":5,"name":"tags","type":"list<string>","required":false,"doc":null},{"id'
    '":7,"name":"shipping","type":"struct<city: required string>","required":false,"doc":null}]},"par'
    'tition_spec":{"spec_id":1,"fields":[{"source_id":3,"field_id":1000,"name":"order_ts_day","transf'
    'orm":"day"},{"source_id":2,"field_id":1001,"name":"customer_id_bucket","transform":"bucket[16]"}'
    ']},"sort_order":{"order_id":1,"fields":[{"source_id":1,"transform":"identity","direction":"asc",'
    '"null_order":"nulls-first"}]},"snapshots":[{"id":"8333017788700497002","parent_id":null,"timesta'
    'mp_ms":1762513200000,"operation":"append","summary":{"added-data-files":"2","added-records":"100'
    '","added-files-size":"4096","changed-partition-count":"1","total-records":"100","total-files-siz'
    'e":"4096","total-data-files":"2","total-delete-files":"0","total-position-deletes":"0","total-eq'
    'uality-deletes":"0"}},{"id":"3051729675574597004","parent_id":"8333017788700497002","timestamp_m'
    's":1762516800123,"operation":"overwrite","summary":{"added-data-files":"1","deleted-data-files":'
    '"1","added-records":"60","deleted-records":"10","added-files-size":"3072","removed-files-size":"'
    '2048","changed-partition-count":"1","total-records":"150","total-files-size":"5120","total-data-'
    'files":"2","total-delete-files":"0","total-position-deletes":"0","total-equality-deletes":"0"}}]'
    ',"properties":{"write.format.default":"parquet","write.parquet.compression-codec":"zstd","owner"'
    ':"data-eng"},"summary":{"total_records":150,"total_data_files":2,"total_files_size":5120}}'
)

VIEW_TEXT = (
    '{"catalog":"sales","namespace":["retail"],"name":"top_orders","uuid":"fa6506c3-7681-40c8-86dc-e3'
    '6561f83385","location":"s3://lakehouse/iceberg/retail/top_orders","sql":"SELECT order_id, amount'
    ' FROM orders","dialect":"trino","default_namespace":["retail","a.b"],"current_version_id":2,"sch'
    'ema":{"schema_id":1,"fields":[{"id":1,"name":"order_id","type":"long","required":true,"doc":"key'
    '"},{"id":2,"name":"amount","type":"decimal(10,2)","required":false,"doc":null},{"id":3,"name":"t'
    'ags","type":"list<string>","required":false,"doc":null}]},"versions":[{"version_id":1,"timestamp'
    '_ms":1762516800000,"sql":"SELECT 1"},{"version_id":2,"timestamp_ms":1762520400000,"sql":"SELECT '
    'order_id, amount FROM orders"}],"properties":{"comment":"top orders"}}'
)

NAMESPACE_TEXT = '{"catalog":"sales","namespace":["retail","a.b"],"properties":{"owner":"data-eng"}}'

GENERIC_TABLE_TEXT = (
    '{"catalog":"sales","namespace":["retail"],"name":"events","format":"delta","base_location":"s3:/'
    '/w/events","doc":"clicks","properties":{"owner":"data-eng"}}'
)


def _stub(path: str, reply: object) -> PolarisStub:
    stub = PolarisStub()
    stub.on("GET", path, httpx.Response(200, json=reply))
    return stub


def test_table_body_is_unchanged():
    """A loaded table is described byte for byte as before."""
    stub = _stub("/api/catalog/v1/sales/namespaces/retail/tables/orders", LOAD_TABLE)
    client = build_client(get_table=GetTableService(TablesPolarisRepo(stub.client())))

    response = client.get("/v1/catalogs/sales/namespaces/retail/tables/orders")

    assert (response.status_code, response.text) == (200, TABLE_TEXT)


def test_view_body_is_unchanged():
    """A loaded view is described byte for byte as before."""
    stub = _stub("/api/catalog/v1/sales/namespaces/retail/views/top_orders", LOAD_VIEW)
    client = build_client(get_view=GetViewService(ViewsPolarisRepo(stub.client())))

    response = client.get("/v1/catalogs/sales/namespaces/retail/views/top_orders")

    assert (response.status_code, response.text) == (200, VIEW_TEXT)


def test_namespace_body_is_unchanged():
    """A loaded namespace is described byte for byte as before."""
    reply = {"namespace": ["retail", "a.b"], "properties": {"owner": "data-eng"}}
    stub = _stub("/api/catalog/v1/sales/namespaces/retail%1Fa.b", reply)
    client = build_client(get_namespace=GetNamespaceService(NamespacesPolarisRepo(stub.client())))

    response = client.get("/v1/catalogs/sales/namespaces/retail%1Fa.b")

    assert (response.status_code, response.text) == (200, NAMESPACE_TEXT)


def test_generic_table_body_is_unchanged():
    """A loaded generic table is described byte for byte as before."""
    reply = {
        "table": {
            "name": "events",
            "format": "delta",
            "base-location": "s3://w/events",
            "doc": "clicks",
            "properties": {"owner": "data-eng"},
        }
    }
    stub = _stub("/api/catalog/polaris/v1/sales/namespaces/retail/generic-tables/events", reply)
    client = build_client(get_generic_table=GetGenericTableService(GenericTablesPolarisRepo(stub.client())))

    response = client.get("/v1/catalogs/sales/namespaces/retail/generic-tables/events")

    assert (response.status_code, response.text) == (200, GENERIC_TABLE_TEXT)
