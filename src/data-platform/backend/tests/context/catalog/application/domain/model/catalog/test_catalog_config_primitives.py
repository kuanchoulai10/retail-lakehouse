"""Test the wire form of a catalog's storage and connection config, as the catalog API reads and writes it.

The ``*_OUT`` dicts were copied literally from the output of ``storage_config_to_dict`` and
``connection_config_to_dict`` before both were retired, and the ``*_IN`` dicts are inputs
``storage_config_from_dict`` / ``connection_config_from_dict`` accepted, decoding to the
objects listed beside them. The input and output shapes differ on purpose: the input
carries the connection secrets, the output never does; the output carries ``user_arn``,
which the catalog service assigns.

The secrets below are obviously fake.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from base.model import validation_message
from context.catalog.application.domain.model.catalog import (
    AuthenticationParameters,
    AuthenticationType,
    ConnectionConfig,
    ConnectionType,
    StorageConfig,
    StorageType,
)

S3_IN: dict[str, Any] = {
    "storage_type": "S3",
    "allowed_locations": ["s3://bucket/", "s3://other/"],
    "region": "us-east-1",
    "role_arn": "arn:aws:iam::123456789012:role/catalog",
    "external_id": "ext-1",
    "endpoint": "http://rustfs:9000",
    "endpoint_internal": "http://rustfs.internal:9000",
    "sts_endpoint": "http://sts:9000",
    "sts_unavailable": True,
    "path_style_access": False,
}
S3 = StorageConfig(
    storage_type=StorageType.S3,
    allowed_locations=("s3://bucket/", "s3://other/"),
    region="us-east-1",
    role_arn="arn:aws:iam::123456789012:role/catalog",
    external_id="ext-1",
    endpoint="http://rustfs:9000",
    endpoint_internal="http://rustfs.internal:9000",
    sts_endpoint="http://sts:9000",
    sts_unavailable=True,
    path_style_access=False,
)
S3_OUT: dict[str, Any] = {
    "storage_type": "S3",
    "allowed_locations": ["s3://bucket/", "s3://other/"],
    "region": "us-east-1",
    "role_arn": "arn:aws:iam::123456789012:role/catalog",
    "external_id": "ext-1",
    "user_arn": None,
    "endpoint": "http://rustfs:9000",
    "endpoint_internal": "http://rustfs.internal:9000",
    "sts_endpoint": "http://sts:9000",
    "sts_unavailable": True,
    "path_style_access": False,
    "tenant_id": None,
    "multi_tenant_app_name": None,
    "consent_url": None,
    "gcs_service_account": None,
}

AZURE_IN: dict[str, Any] = {
    "storage_type": "AZURE",
    "allowed_locations": ["abfss://c@acct.dfs.core.windows.net/"],
    "tenant_id": "tenant-1",
    "multi_tenant_app_name": "app-1",
    "consent_url": "https://consent.example/",
}
AZURE = StorageConfig(
    storage_type=StorageType.AZURE,
    allowed_locations=("abfss://c@acct.dfs.core.windows.net/",),
    tenant_id="tenant-1",
    multi_tenant_app_name="app-1",
    consent_url="https://consent.example/",
)
AZURE_OUT: dict[str, Any] = {
    "storage_type": "AZURE",
    "allowed_locations": ["abfss://c@acct.dfs.core.windows.net/"],
    "region": None,
    "role_arn": None,
    "external_id": None,
    "user_arn": None,
    "endpoint": None,
    "endpoint_internal": None,
    "sts_endpoint": None,
    "sts_unavailable": None,
    "path_style_access": None,
    "tenant_id": "tenant-1",
    "multi_tenant_app_name": "app-1",
    "consent_url": "https://consent.example/",
    "gcs_service_account": None,
}

GCS_IN: dict[str, Any] = {
    "storage_type": "GCS",
    "allowed_locations": ["gs://bucket/"],
    "gcs_service_account": "sa@proj.iam.gserviceaccount.com",
}
GCS = StorageConfig(
    storage_type=StorageType.GCS,
    allowed_locations=("gs://bucket/",),
    gcs_service_account="sa@proj.iam.gserviceaccount.com",
)
GCS_OUT: dict[str, Any] = {
    "storage_type": "GCS",
    "allowed_locations": ["gs://bucket/"],
    "region": None,
    "role_arn": None,
    "external_id": None,
    "user_arn": None,
    "endpoint": None,
    "endpoint_internal": None,
    "sts_endpoint": None,
    "sts_unavailable": None,
    "path_style_access": None,
    "tenant_id": None,
    "multi_tenant_app_name": None,
    "consent_url": None,
    "gcs_service_account": "sa@proj.iam.gserviceaccount.com",
}

FILE_IN: dict[str, Any] = {"storage_type": "FILE", "allowed_locations": ["file:///tmp/warehouse/"]}
FILE = StorageConfig(storage_type=StorageType.FILE, allowed_locations=("file:///tmp/warehouse/",))
FILE_OUT: dict[str, Any] = {
    "storage_type": "FILE",
    "allowed_locations": ["file:///tmp/warehouse/"],
    "region": None,
    "role_arn": None,
    "external_id": None,
    "user_arn": None,
    "endpoint": None,
    "endpoint_internal": None,
    "sts_endpoint": None,
    "sts_unavailable": None,
    "path_style_access": None,
    "tenant_id": None,
    "multi_tenant_app_name": None,
    "consent_url": None,
    "gcs_service_account": None,
}

MINIMAL_IN: dict[str, Any] = {"storage_type": "S3"}
MINIMAL = StorageConfig(storage_type=StorageType.S3)
MINIMAL_OUT: dict[str, Any] = {
    "storage_type": "S3",
    "allowed_locations": [],
    "region": None,
    "role_arn": None,
    "external_id": None,
    "user_arn": None,
    "endpoint": None,
    "endpoint_internal": None,
    "sts_endpoint": None,
    "sts_unavailable": None,
    "path_style_access": None,
    "tenant_id": None,
    "multi_tenant_app_name": None,
    "consent_url": None,
    "gcs_service_account": None,
}

STORAGE_CASES = [
    pytest.param(S3_IN, S3, S3_OUT, id="S3"),
    pytest.param(AZURE_IN, AZURE, AZURE_OUT, id="AZURE"),
    pytest.param(GCS_IN, GCS, GCS_OUT, id="GCS"),
    pytest.param(FILE_IN, FILE, FILE_OUT, id="FILE"),
    pytest.param(MINIMAL_IN, MINIMAL, MINIMAL_OUT, id="minimal"),
]

OAUTH_IN: dict[str, Any] = {
    "connection_type": "REST",
    "uri": "https://remote.example/api/catalog",
    "authentication": {
        "authentication_type": "OAUTH",
        "token_uri": "https://remote.example/oauth/tokens",
        "client_id": "remote-client",
        "client_secret": "fake-client-secret",
        "scopes": ["PRINCIPAL_ROLE:ALL", "x"],
    },
}
OAUTH = ConnectionConfig(
    connection_type=ConnectionType.REST,
    uri="https://remote.example/api/catalog",
    authentication=AuthenticationParameters(
        authentication_type=AuthenticationType.OAUTH,
        token_uri="https://remote.example/oauth/tokens",
        client_id="remote-client",
        client_secret="fake-client-secret",
        scopes=("PRINCIPAL_ROLE:ALL", "x"),
    ),
)
OAUTH_OUT: dict[str, Any] = {
    "connection_type": "REST",
    "uri": "https://remote.example/api/catalog",
    "authentication": {
        "authentication_type": "OAUTH",
        "token_uri": "https://remote.example/oauth/tokens",
        "client_id": "remote-client",
        "scopes": ["PRINCIPAL_ROLE:ALL", "x"],
        "role_arn": None,
        "role_session_name": None,
        "external_id": None,
        "signing_region": None,
        "signing_name": None,
    },
}

BEARER_IN: dict[str, Any] = {
    "connection_type": "REST",
    "uri": "https://remote.example/api/catalog",
    "authentication": {"authentication_type": "BEARER", "bearer_token": "fake-bearer-token"},
}
BEARER = ConnectionConfig(
    connection_type=ConnectionType.REST,
    uri="https://remote.example/api/catalog",
    authentication=AuthenticationParameters(
        authentication_type=AuthenticationType.BEARER, bearer_token="fake-bearer-token"
    ),
)
BEARER_OUT: dict[str, Any] = {
    "connection_type": "REST",
    "uri": "https://remote.example/api/catalog",
    "authentication": {
        "authentication_type": "BEARER",
        "token_uri": None,
        "client_id": None,
        "scopes": [],
        "role_arn": None,
        "role_session_name": None,
        "external_id": None,
        "signing_region": None,
        "signing_name": None,
    },
}

SIGV4_IN: dict[str, Any] = {
    "connection_type": "REST",
    "uri": "https://glue.example/iceberg",
    "authentication": {
        "authentication_type": "SIGV4",
        "role_arn": "arn:aws:iam::123456789012:role/remote",
        "role_session_name": "polaris",
        "external_id": "ext-2",
        "signing_region": "us-west-2",
        "signing_name": "glue",
    },
}
SIGV4 = ConnectionConfig(
    connection_type=ConnectionType.REST,
    uri="https://glue.example/iceberg",
    authentication=AuthenticationParameters(
        authentication_type=AuthenticationType.SIGV4,
        role_arn="arn:aws:iam::123456789012:role/remote",
        role_session_name="polaris",
        external_id="ext-2",
        signing_region="us-west-2",
        signing_name="glue",
    ),
)
SIGV4_OUT: dict[str, Any] = {
    "connection_type": "REST",
    "uri": "https://glue.example/iceberg",
    "authentication": {
        "authentication_type": "SIGV4",
        "token_uri": None,
        "client_id": None,
        "scopes": [],
        "role_arn": "arn:aws:iam::123456789012:role/remote",
        "role_session_name": "polaris",
        "external_id": "ext-2",
        "signing_region": "us-west-2",
        "signing_name": "glue",
    },
}

IMPLICIT_IN: dict[str, Any] = {
    "connection_type": "HADOOP",
    "uri": "hdfs://namenode/warehouse",
    "authentication": {"authentication_type": "IMPLICIT"},
}
IMPLICIT = ConnectionConfig(
    connection_type=ConnectionType.HADOOP,
    uri="hdfs://namenode/warehouse",
    authentication=AuthenticationParameters(authentication_type=AuthenticationType.IMPLICIT),
)
IMPLICIT_OUT: dict[str, Any] = {
    "connection_type": "HADOOP",
    "uri": "hdfs://namenode/warehouse",
    "authentication": {
        "authentication_type": "IMPLICIT",
        "token_uri": None,
        "client_id": None,
        "scopes": [],
        "role_arn": None,
        "role_session_name": None,
        "external_id": None,
        "signing_region": None,
        "signing_name": None,
    },
}

HIVE_IN: dict[str, Any] = {
    "connection_type": "HIVE",
    "uri": "thrift://hive:9083",
    "authentication": {"authentication_type": "IMPLICIT"},
}
HIVE = ConnectionConfig(
    connection_type=ConnectionType.HIVE,
    uri="thrift://hive:9083",
    authentication=AuthenticationParameters(authentication_type=AuthenticationType.IMPLICIT),
)
HIVE_OUT: dict[str, Any] = {
    "connection_type": "HIVE",
    "uri": "thrift://hive:9083",
    "authentication": {
        "authentication_type": "IMPLICIT",
        "token_uri": None,
        "client_id": None,
        "scopes": [],
        "role_arn": None,
        "role_session_name": None,
        "external_id": None,
        "signing_region": None,
        "signing_name": None,
    },
}

NO_URI_IN: dict[str, Any] = {
    "connection_type": "REST",
    "authentication": {"authentication_type": "OAUTH", "client_id": "c"},
}
NO_URI = ConnectionConfig(
    connection_type=ConnectionType.REST,
    authentication=AuthenticationParameters(authentication_type=AuthenticationType.OAUTH, client_id="c"),
)
NO_URI_OUT: dict[str, Any] = {
    "connection_type": "REST",
    "uri": None,
    "authentication": {
        "authentication_type": "OAUTH",
        "token_uri": None,
        "client_id": "c",
        "scopes": [],
        "role_arn": None,
        "role_session_name": None,
        "external_id": None,
        "signing_region": None,
        "signing_name": None,
    },
}

CONNECTION_CASES = [
    pytest.param(OAUTH_IN, OAUTH, OAUTH_OUT, id="OAUTH"),
    pytest.param(BEARER_IN, BEARER, BEARER_OUT, id="BEARER"),
    pytest.param(SIGV4_IN, SIGV4, SIGV4_OUT, id="SIGV4"),
    pytest.param(IMPLICIT_IN, IMPLICIT, IMPLICIT_OUT, id="IMPLICIT"),
    pytest.param(HIVE_IN, HIVE, HIVE_OUT, id="HIVE"),
    pytest.param(NO_URI_IN, NO_URI, NO_URI_OUT, id="no-uri"),
]

SECRETS = ("client_secret", "bearer_token")


@pytest.mark.parametrize(("given", "expected", "described"), STORAGE_CASES)
def test_storage_input_decodes_to_the_config(given: dict[str, Any], expected: StorageConfig, described: Any) -> None:  # noqa: ANN401, ARG001
    """Every input the old converter accepted decodes to the same storage config."""
    assert StorageConfig.from_primitives(given) == expected


@pytest.mark.parametrize(("given", "expected", "described"), STORAGE_CASES)
def test_storage_config_encodes_to_golden(given: Any, expected: StorageConfig, described: dict[str, Any]) -> None:  # noqa: ANN401, ARG001
    """The described storage config keeps every field, unset ones null, in the old key order."""
    assert json.dumps(expected.to_primitives()) == json.dumps(described)


@pytest.mark.parametrize(("given", "expected", "described"), STORAGE_CASES)
def test_storage_config_round_trips(given: Any, expected: StorageConfig, described: dict[str, Any]) -> None:  # noqa: ANN401, ARG001
    """A described storage config reads back as the same config."""
    assert StorageConfig.from_primitives(described) == expected


def test_user_arn_reads_back_from_a_description() -> None:
    """``user_arn`` is a field of the config, so a description holding it reads back with it."""
    described = {**S3_OUT, "user_arn": "arn:aws:iam::1:user/polaris"}

    assert StorageConfig.from_primitives(described).user_arn == "arn:aws:iam::1:user/polaris"


@pytest.mark.parametrize(("given", "expected", "described"), CONNECTION_CASES)
def test_connection_input_decodes_to_the_config(
    given: dict[str, Any], expected: ConnectionConfig, described: Any
) -> None:  # noqa: ANN401, ARG001
    """Every input the old converter accepted decodes to the same connection, secrets included."""
    assert ConnectionConfig.from_primitives(given) == expected


@pytest.mark.parametrize(("given", "expected", "described"), CONNECTION_CASES)
def test_connection_config_encodes_to_golden(given: Any, expected: ConnectionConfig, described: dict[str, Any]) -> None:  # noqa: ANN401, ARG001
    """The described connection keeps every non-secret field, unset ones null, in the old key order."""
    assert json.dumps(expected.to_primitives()) == json.dumps(described)


@pytest.mark.parametrize(("given", "expected", "described"), CONNECTION_CASES)
def test_described_connection_has_no_secret_keys(given: Any, expected: ConnectionConfig, described: Any) -> None:  # noqa: ANN401, ARG001
    """The description never carries a secret: neither its key nor its value."""
    primitives = expected.to_primitives()

    assert not set(SECRETS) & set(primitives["authentication"])
    assert "fake-client-secret" not in json.dumps(primitives)
    assert "fake-bearer-token" not in json.dumps(primitives)


def test_decoded_connection_keeps_its_secrets() -> None:
    """The secrets are read in, so the catalog service can be sent them."""
    oauth = ConnectionConfig.from_primitives(OAUTH_IN).authentication
    bearer = ConnectionConfig.from_primitives(BEARER_IN).authentication

    assert oauth is not None
    assert oauth.client_secret == "fake-client-secret"
    assert bearer is not None
    assert bearer.bearer_token == "fake-bearer-token"


def test_connection_without_authentication_encodes_it_as_null() -> None:
    """A connection read back without authentication parameters describes them as null."""
    config = ConnectionConfig(connection_type=ConnectionType.REST, uri="https://remote.example/api/catalog")

    assert json.dumps(config.to_primitives()) == json.dumps(
        {"connection_type": "REST", "uri": "https://remote.example/api/catalog", "authentication": None}
    )


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({}, "storage_type: Field required"),
        ({"allowed_locations": []}, "storage_type: Field required"),
        ({"storage_type": "NFS"}, "storage_type: Input should be 'S3', 'AZURE', 'GCS' or 'FILE'"),
        ({"storage_type": "S3", "bucket": "b"}, "bucket: Extra inputs are not permitted"),
        ({"storage_type": "AZURE"}, "tenant_id: required for AZURE storage"),
        ({"storage_type": "AZURE", "tenant_id": ""}, "tenant_id: required for AZURE storage"),
        ({"storage_type": "S3", "allowed_locations": "s3://b/"}, "allowed_locations: Input should be a valid array"),
        ({"storage_type": "S3", "allowed_locations": [1]}, "allowed_locations.0: Input should be a valid string"),
        ({"storage_type": "S3", "path_style_access": "yes"}, "path_style_access: Input should be a valid boolean"),
        ({"storage_type": "S3", "region": 1}, "region: Input should be a valid string"),
    ],
)
def test_invalid_storage_input_names_the_field(data: dict[str, Any], message: str) -> None:
    """Invalid storage input is rejected with a one-line message naming the field."""
    with pytest.raises(ValidationError) as raised:
        StorageConfig.from_primitives(data)

    assert validation_message(raised.value) == message


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (
            {"uri": "https://r", "authentication": {"authentication_type": "IMPLICIT"}},
            "connection_type: Field required",
        ),
        ({**OAUTH_IN, "connection_type": "JDBC"}, "connection_type: Input should be 'REST', 'HADOOP' or 'HIVE'"),
        ({**OAUTH_IN, "port": 1}, "port: Extra inputs are not permitted"),
        ({**OAUTH_IN, "uri": 1}, "uri: Input should be a valid string"),
        ({**OAUTH_IN, "authentication": {}}, "authentication.authentication_type: Field required"),
        (
            {**OAUTH_IN, "authentication": {"authentication_type": "KERBEROS"}},
            "authentication.authentication_type: Input should be 'OAUTH', 'BEARER', 'SIGV4' or 'IMPLICIT'",
        ),
        (
            {**OAUTH_IN, "authentication": {"authentication_type": "OAUTH", "password": "p"}},
            "authentication.password: Extra inputs are not permitted",
        ),
        (
            {**OAUTH_IN, "authentication": {"authentication_type": "OAUTH", "bearer_token": "fake-bearer-token"}},
            "authentication: bearer_token does not apply to OAUTH authentication",
        ),
        (
            {
                **OAUTH_IN,
                "authentication": {"authentication_type": "IMPLICIT", "scopes": ["a"], "signing_name": "glue"},
            },
            "authentication: scopes, signing_name does not apply to IMPLICIT authentication",
        ),
        (
            {**OAUTH_IN, "authentication": {"authentication_type": "OAUTH", "scopes": "PRINCIPAL_ROLE:ALL"}},
            "authentication.scopes: Input should be a valid array",
        ),
        ({**OAUTH_IN, "authentication": "OAUTH"}, "authentication: Input should be an object"),
    ],
)
def test_invalid_connection_input_names_the_field(data: dict[str, Any], message: str) -> None:
    """Invalid connection input is rejected with a one-line message naming the field."""
    with pytest.raises(ValidationError) as raised:
        ConnectionConfig.from_primitives(data)

    assert validation_message(raised.value) == message


def test_rejection_message_never_carries_a_secret() -> None:
    """A rejected input that holds a secret does not echo it in the message."""
    data = {**OAUTH_IN, "authentication": {"authentication_type": "OAUTH", "bearer_token": "fake-bearer-token"}}

    with pytest.raises(ValidationError) as raised:
        ConnectionConfig.from_primitives(data)

    assert "fake-bearer-token" not in validation_message(raised.value)


def test_azure_storage_without_tenant_is_refused_in_code() -> None:
    """The AZURE tenant rule holds for a config built in code too."""
    with pytest.raises(ValidationError, match="required for AZURE storage"):
        StorageConfig(storage_type=StorageType.AZURE)


def test_authentication_field_of_another_type_is_refused_in_code() -> None:
    """A field of another authentication type is refused for a value built in code too."""
    with pytest.raises(ValidationError, match="token_uri does not apply to BEARER authentication"):
        AuthenticationParameters(authentication_type=AuthenticationType.BEARER, token_uri="https://t")


@pytest.mark.parametrize(
    "build",
    [
        lambda: StorageConfig(storage_type="S3"),  # ty: ignore[invalid-argument-type]
        lambda: StorageConfig(storage_type=StorageType.S3, allowed_locations=["s3://b/"]),  # ty: ignore[invalid-argument-type]
        lambda: ConnectionConfig(connection_type="REST"),  # ty: ignore[invalid-argument-type]
        lambda: AuthenticationParameters(authentication_type=AuthenticationType.OAUTH, scopes=["a"]),  # ty: ignore[invalid-argument-type]
    ],
)
def test_code_construction_is_strict(build: Any) -> None:  # noqa: ANN401
    """Built in code, a plain string is no enum and a list is no tuple."""
    with pytest.raises(ValidationError):
        build()


@pytest.mark.parametrize(
    ("value", "field", "new"),
    [
        (S3, "region", "eu-west-1"),
        (OAUTH, "uri", "https://other"),
        (OAUTH.authentication, "client_id", "other"),
    ],
)
def test_config_value_objects_are_immutable(value: Any, field: str, new: str) -> None:  # noqa: ANN401
    """Storage, connection and authentication configs cannot be changed in place."""
    with pytest.raises(ValidationError):
        setattr(value, field, new)
