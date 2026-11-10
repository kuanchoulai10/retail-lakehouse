"""Test that the catalogs repo sends the exact Polaris management requests and maps the replies."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from context.catalog.adapter.outbound.catalog.polaris import CatalogsPolarisRepo
from context.catalog.application.exceptions import (
    CatalogUnavailableError,
    ConflictError,
    ValidationError,
)
from context.catalog.application.port.outbound.catalog import (
    AuthenticationParameters,
    AuthenticationType,
    Catalog,
    CatalogId,
    CatalogType,
    ConnectionConfig,
    ConnectionType,
    StorageConfig,
    StorageType,
)
from tests.context.catalog.adapter.outbound.shared.polaris.polaris_stub import (
    PolarisStub,
)

CATALOGS = "/api/management/v1/catalogs"
NOW = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
NOW_MS = 1794052800000

POLARIS_STORAGE: dict[str, Any] = {
    "storageType": "S3",
    "allowedLocations": ["s3://bucket/"],
    "endpoint": "http://rustfs:9000",
    "pathStyleAccess": True,
}


def _polaris_catalog(name: str = "sales", version: int = 1, **storage: Any) -> dict[str, Any]:  # noqa: ANN401
    return {
        "type": "INTERNAL",
        "name": name,
        "properties": {"default-base-location": f"s3://bucket/{name}"},
        "createTimestamp": NOW_MS,
        "lastUpdateTimestamp": NOW_MS,
        "entityVersion": version,
        "storageConfigInfo": POLARIS_STORAGE | storage,
    }


def _catalog(name: str = "sales", version: int = 0) -> Catalog:
    return Catalog(
        id=CatalogId.of(name),
        type=CatalogType.INTERNAL,
        properties={"default-base-location": f"s3://bucket/{name}"},
        storage_config=StorageConfig(
            storage_type=StorageType.S3,
            allowed_locations=("s3://bucket/",),
            endpoint="http://rustfs:9000",
            path_style_access=True,
        ),
        entity_version=version,
    )


OAUTH_CONNECTION = ConnectionConfig(
    connection_type=ConnectionType.REST,
    uri="https://remote.example/api/catalog",
    authentication=AuthenticationParameters(
        authentication_type=AuthenticationType.OAUTH,
        token_uri="https://remote.example/oauth/tokens",
        client_id="remote-client",
        client_secret="remote-s3cr3t",
        scopes=("PRINCIPAL_ROLE:ALL",),
    ),
)
POLARIS_OAUTH_CONNECTION: dict[str, Any] = {
    "connectionType": "ICEBERG_REST",
    "uri": "https://remote.example/api/catalog",
    "authenticationParameters": {
        "authenticationType": "OAUTH",
        "tokenUri": "https://remote.example/oauth/tokens",
        "clientId": "remote-client",
        "clientSecret": "remote-s3cr3t",
        "scopes": ["PRINCIPAL_ROLE:ALL"],
    },
}


def _body(request: httpx.Request) -> Any:  # noqa: ANN401
    return json.loads(request.content)


def test_create_posts_the_catalog_wrapped_in_catalog():
    """Create sends POST /catalogs with ``{"catalog": {...}}`` and returns what Polaris saved."""
    stub = PolarisStub()
    stub.on("POST", CATALOGS, httpx.Response(201, json=_polaris_catalog()))

    saved = CatalogsPolarisRepo(stub.client()).create(_catalog())

    (request,) = stub.requests
    assert request.method == "POST"
    assert request.url.path == CATALOGS
    assert _body(request) == {
        "catalog": {
            "name": "sales",
            "type": "INTERNAL",
            "properties": {"default-base-location": "s3://bucket/sales"},
            "storageConfigInfo": POLARIS_STORAGE,
        }
    }
    assert (saved.id, saved.entity_version, saved.created_at) == (CatalogId.of("sales"), 1, NOW)


def test_update_puts_the_current_entity_version():
    """Update sends PUT /catalogs/{name} with currentEntityVersion, properties and storageConfigInfo."""
    stub = PolarisStub()
    stub.on("PUT", f"{CATALOGS}/sales", httpx.Response(200, json=_polaris_catalog(version=4)))

    saved = CatalogsPolarisRepo(stub.client()).update(_catalog(version=3))

    (request,) = stub.requests
    assert (request.method, request.url.path) == ("PUT", f"{CATALOGS}/sales")
    assert _body(request) == {
        "currentEntityVersion": 3,
        "properties": {"default-base-location": "s3://bucket/sales"},
        "storageConfigInfo": POLARIS_STORAGE,
    }
    assert request.content == (
        b'{"currentEntityVersion":3,"properties":{"default-base-location":"s3://bucket/sales"},'
        b'"storageConfigInfo":{"storageType":"S3","allowedLocations":["s3://bucket/"],"endpoint":"http://rustfs:9000",'
        b'"pathStyleAccess":true}}'
    )
    assert saved.entity_version == 4


def test_update_of_a_stale_version_is_a_conflict():
    """Polaris's 409 on a stale entity version reaches the caller as a conflict."""
    stub = PolarisStub()
    stub.on("PUT", f"{CATALOGS}/sales", httpx.Response(409, json={"error": {"message": "entity version stale"}}))

    with pytest.raises(ConflictError, match="entity version stale"):
        CatalogsPolarisRepo(stub.client()).update(_catalog(version=3))


def test_delete_sends_delete_on_the_catalog():
    """Delete sends DELETE /catalogs/{name}."""
    stub = PolarisStub()
    stub.on("DELETE", f"{CATALOGS}/sales", httpx.Response(204))

    CatalogsPolarisRepo(stub.client()).delete(CatalogId.of("sales"))

    (request,) = stub.requests
    assert (request.method, request.url.path) == ("DELETE", f"{CATALOGS}/sales")


def test_delete_of_a_catalog_that_is_not_empty_reports_polaris():
    """Polaris refusing to drop a catalog that still holds content reaches the caller with its message."""
    stub = PolarisStub()
    message = "Catalog 'sales' cannot be dropped, it is not empty"
    stub.on("DELETE", f"{CATALOGS}/sales", httpx.Response(400, json={"error": {"message": message}}))

    with pytest.raises(ValidationError, match=message):
        CatalogsPolarisRepo(stub.client()).delete(CatalogId.of("sales"))


def test_get_maps_every_polaris_field():
    """Get maps the Polaris catalog, its storage config and its timestamps."""
    stub = PolarisStub()
    reply = _polaris_catalog(version=7, userArn="arn:aws:iam::1:user/x", region="us-east-1")
    reply["lastUpdateTimestamp"] = NOW_MS + 1000
    stub.on("GET", f"{CATALOGS}/sales", httpx.Response(200, json=reply))

    catalog = CatalogsPolarisRepo(stub.client()).get(CatalogId.of("sales"))

    assert catalog is not None
    assert catalog.id == CatalogId.of("sales")
    assert catalog.type is CatalogType.INTERNAL
    assert catalog.properties == {"default-base-location": "s3://bucket/sales"}
    assert catalog.storage_config == StorageConfig(
        storage_type=StorageType.S3,
        allowed_locations=("s3://bucket/",),
        endpoint="http://rustfs:9000",
        path_style_access=True,
        user_arn="arn:aws:iam::1:user/x",
        region="us-east-1",
    )
    assert catalog.entity_version == 7
    assert catalog.created_at == NOW
    assert catalog.updated_at == datetime(2026, 11, 7, 12, 0, 1, tzinfo=UTC)


def test_get_of_a_missing_catalog_is_none():
    """A 404 from Polaris means the catalog does not exist."""
    stub = PolarisStub()
    stub.on("GET", f"{CATALOGS}/nope", httpx.Response(404, json={"error": {"message": "Catalog not found: nope"}}))

    assert CatalogsPolarisRepo(stub.client()).get(CatalogId.of("nope")) is None


def test_list_all_returns_every_catalog():
    """List sends GET /catalogs and maps each catalog."""
    stub = PolarisStub()
    stub.on("GET", CATALOGS, httpx.Response(200, json={"catalogs": [_polaris_catalog("a"), _polaris_catalog("b")]}))

    catalogs = CatalogsPolarisRepo(stub.client()).list_all()

    assert [c.id for c in catalogs] == [CatalogId.of("a"), CatalogId.of("b")]


def test_catalog_name_is_percent_encoded_in_the_path():
    """A name with characters that are not URL-safe is encoded as one path segment."""
    stub = PolarisStub()
    stub.on("GET", f"{CATALOGS}/my%20cat%2Fx", httpx.Response(200, json=_polaris_catalog("my cat/x")))

    catalog = CatalogsPolarisRepo(stub.client()).get(CatalogId.of("my cat/x"))

    assert catalog is not None
    assert catalog.id == CatalogId.of("my cat/x")


def test_create_external_catalog_sends_the_exact_connection_config_info():
    """An external catalog's connection, secret included, is sent as ``connectionConfigInfo``."""
    stub = PolarisStub()
    reply = _polaris_catalog() | {"type": "EXTERNAL", "connectionConfigInfo": {"connectionType": "ICEBERG_REST"}}
    stub.on("POST", CATALOGS, httpx.Response(201, json=reply))
    catalog = _catalog()
    catalog.type = CatalogType.EXTERNAL
    catalog.connection_config = OAUTH_CONNECTION

    CatalogsPolarisRepo(stub.client()).create(catalog)

    (request,) = stub.requests
    assert _body(request)["catalog"]["type"] == "EXTERNAL"
    assert _body(request)["catalog"]["connectionConfigInfo"] == POLARIS_OAUTH_CONNECTION
    assert request.content == (
        b'{"catalog":{"name":"sales","type":"EXTERNAL","properties":{"default-base-location":"s3://bucket/sales"},'
        b'"storageConfigInfo":{"storageType":"S3","allowedLocations":["s3://bucket/"],"endpoint":"http://rustfs:9000",'
        b'"pathStyleAccess":true},"connectionConfigInfo":{"connectionType":"ICEBERG_REST",'
        b'"uri":"https://remote.example/api/catalog","authenticationParameters":{"authenticationType":"OAUTH",'
        b'"tokenUri":"https://remote.example/oauth/tokens","clientId":"remote-client","clientSecret":"remote-s3cr3t",'
        b'"scopes":["PRINCIPAL_ROLE:ALL"]}}}}'
    )


@pytest.mark.parametrize(
    ("authentication", "expected"),
    [
        (
            {"authenticationType": "BEARER", "bearerToken": "remote-token"},
            AuthenticationParameters(authentication_type=AuthenticationType.BEARER),
        ),
        (
            {
                "authenticationType": "SIGV4",
                "roleArn": "arn:aws:iam::1:role/r",
                "roleSessionName": "polaris",
                "externalId": "ext",
                "signingRegion": "us-west-2",
                "signingName": "glue",
            },
            AuthenticationParameters(
                authentication_type=AuthenticationType.SIGV4,
                role_arn="arn:aws:iam::1:role/r",
                role_session_name="polaris",
                external_id="ext",
                signing_region="us-west-2",
                signing_name="glue",
            ),
        ),
        ({"authenticationType": "IMPLICIT"}, AuthenticationParameters(authentication_type=AuthenticationType.IMPLICIT)),
        (
            POLARIS_OAUTH_CONNECTION["authenticationParameters"],
            AuthenticationParameters(
                authentication_type=AuthenticationType.OAUTH,
                token_uri="https://remote.example/oauth/tokens",
                client_id="remote-client",
                scopes=("PRINCIPAL_ROLE:ALL",),
            ),
        ),
    ],
    ids=["bearer", "sigv4", "implicit", "oauth"],
)
def test_get_maps_the_connection_config_info_and_drops_any_secret(authentication: dict[str, Any], expected):
    """The read maps the connection; a secret Polaris might return is never kept."""
    stub = PolarisStub()
    connection = {
        "connectionType": "HIVE",
        "uri": "thrift://hive:9083",
        "authenticationParameters": authentication,
        "serviceIdentity": {"identityType": "AWS_IAM", "iamArn": "arn:aws:iam::1:user/polaris"},
    }
    stub.on(
        "GET", f"{CATALOGS}/sales", httpx.Response(200, json=_polaris_catalog() | {"connectionConfigInfo": connection})
    )

    catalog = CatalogsPolarisRepo(stub.client()).get(CatalogId.of("sales"))

    assert catalog is not None
    assert catalog.connection_config == ConnectionConfig(
        connection_type=ConnectionType.HIVE, uri="thrift://hive:9083", authentication=expected
    )


def test_get_of_a_catalog_without_connection_has_none():
    """An internal catalog reads back without a connection."""
    stub = PolarisStub()
    stub.on("GET", f"{CATALOGS}/sales", httpx.Response(200, json=_polaris_catalog()))

    catalog = CatalogsPolarisRepo(stub.client()).get(CatalogId.of("sales"))

    assert catalog is not None
    assert catalog.connection_config is None


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"type": "FEDERATED"}, "unknown catalog type 'FEDERATED'"),
        ({"storageConfigInfo": {"storageType": "NFS"}}, "unknown storage type 'NFS'"),
        ({"connectionConfigInfo": {"connectionType": "JDBC"}}, "unknown connection type 'JDBC'"),
        (
            {
                "connectionConfigInfo": {
                    "connectionType": "HIVE",
                    "authenticationParameters": {"authenticationType": "X"},
                }
            },
            "unknown authentication type 'X'",
        ),
    ],
)
def test_unknown_enum_value_from_polaris_is_unavailable(change: dict[str, Any], message: str):
    """A value this backend does not know is a clear upstream fault, not an unhandled error."""
    stub = PolarisStub()
    stub.on("GET", f"{CATALOGS}/sales", httpx.Response(200, json=_polaris_catalog() | change))

    with pytest.raises(
        CatalogUnavailableError, match=f"Polaris returned catalog sales in a form this backend cannot read: .*{message}"
    ):
        CatalogsPolarisRepo(stub.client()).get(CatalogId.of("sales"))


@pytest.mark.parametrize(
    "change",
    [
        {"properties": {"retention": 7}},
        {"storageConfigInfo": {"storageType": "S3", "stsUnavailable": "yes"}},
        {"storageConfigInfo": {"storageType": "AZURE", "allowedLocations": ["abfss://c@a/"]}},
        {"connectionConfigInfo": {"connectionType": "HIVE", "uri": 9083}},
    ],
)
def test_ill_typed_value_from_polaris_is_unavailable(change: dict[str, Any]):
    """A value of the wrong type, or a storage that breaks a domain rule, is an upstream fault: a 502."""
    stub = PolarisStub()
    stub.on("GET", f"{CATALOGS}/sales", httpx.Response(200, json=_polaris_catalog() | change))

    with pytest.raises(
        CatalogUnavailableError, match="Polaris returned catalog sales in a form this backend cannot read"
    ):
        CatalogsPolarisRepo(stub.client()).get(CatalogId.of("sales"))


def test_read_catalog_holds_domain_types():
    """A catalog read from Polaris holds tuples and enums, never the JSON lists and strings it came as."""
    stub = PolarisStub()
    reply = _polaris_catalog() | {
        "type": "EXTERNAL",
        "connectionConfigInfo": {
            "connectionType": "ICEBERG_REST",
            "authenticationParameters": {"authenticationType": "OAUTH", "clientId": "c", "scopes": ["a"]},
        },
    }
    stub.on("GET", f"{CATALOGS}/sales", httpx.Response(200, json=reply))

    catalog = CatalogsPolarisRepo(stub.client()).get(CatalogId.of("sales"))

    assert catalog is not None
    assert type(catalog.type) is CatalogType
    assert type(catalog.storage_config.storage_type) is StorageType
    assert type(catalog.storage_config.allowed_locations) is tuple
    assert catalog.connection_config is not None
    assert type(catalog.connection_config.connection_type) is ConnectionType
    assert catalog.connection_config.authentication is not None
    assert type(catalog.connection_config.authentication.scopes) is tuple


_HTML = httpx.Response(200, text="<html>proxy error</html>", headers={"content-type": "text/html"})
_JSON_LIST = httpx.Response(200, json=["sales"])
_OPERATIONS = {
    "create": ("POST", CATALOGS, lambda repo: repo.create(_catalog())),
    "get": ("GET", f"{CATALOGS}/sales", lambda repo: repo.get(CatalogId.of("sales"))),
    "list_all": ("GET", CATALOGS, lambda repo: repo.list_all()),
    "update": ("PUT", f"{CATALOGS}/sales", lambda repo: repo.update(_catalog(version=1))),
}


@pytest.mark.parametrize("operation", sorted(_OPERATIONS))
@pytest.mark.parametrize("reply", [_HTML, _JSON_LIST], ids=["html", "json-list"])
def test_unreadable_reply_is_unavailable_on_every_operation(operation: str, reply: httpx.Response):
    """A 200 that is HTML or not a JSON object is a CatalogUnavailableError (502), never a 500."""
    method, path, call = _OPERATIONS[operation]
    stub = PolarisStub()
    stub.on(method, path, reply)

    with pytest.raises(CatalogUnavailableError, match="in a form this backend cannot read"):
        call(CatalogsPolarisRepo(stub.client()))


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"catalogs": ["sales"]},
        {"catalogs": [{k: v for k, v in _polaris_catalog().items() if k != "name"}]},
    ],
    ids=["no-catalogs", "string-item", "item-without-name"],
)
def test_unreadable_catalog_listing_is_unavailable(body: dict[str, Any]):
    """A listing without ``catalogs``, or with an item that is not a named catalog object, is a 502."""
    stub = PolarisStub()
    stub.on("GET", CATALOGS, httpx.Response(200, json=body))

    with pytest.raises(CatalogUnavailableError, match="the catalog list in a form this backend cannot read"):
        CatalogsPolarisRepo(stub.client()).list_all()


@pytest.mark.parametrize("missing", ["name", "type", "storageConfigInfo", "entityVersion"])
def test_catalog_without_a_required_field_is_unavailable(missing: str):
    """A required field is never defaulted; a catalog without one is a 502 naming the catalog."""
    stub = PolarisStub()
    body = {k: v for k, v in _polaris_catalog().items() if k != missing}
    stub.on("GET", f"{CATALOGS}/sales", httpx.Response(200, json=body))

    with pytest.raises(CatalogUnavailableError, match="catalog sales in a form this backend cannot read"):
        CatalogsPolarisRepo(stub.client()).get(CatalogId.of("sales"))
