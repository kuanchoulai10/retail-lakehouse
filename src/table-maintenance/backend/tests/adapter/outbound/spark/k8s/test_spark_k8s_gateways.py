from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from adapter.outbound.spark.k8s import (
    DeleteMaintenanceJobK8sGateway,
    ReadMaintenanceJobK8sGateway,
    SparkK8sConfig,
    SubmitMaintenanceJobK8sGateway,
    build_spark_application,
)
from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.service.spark_application_name import spark_application_name
from application.port.outbound.spark.delete_maintenance_job import (
    DeleteMaintenanceJobGatewayInput,
)
from application.port.outbound.spark.read_maintenance_job import (
    ReadMaintenanceJobGatewayInput,
)
from application.port.outbound.spark.submit_maintenance_job import (
    SubmitMaintenanceJobGatewayInput,
)
from kubernetes.client.exceptions import ApiException

CONFIG = SparkK8sConfig(
    image="table-maintenance-spark:dev",
    service_account="spark",
    catalog_uri="http://polaris.lakehouse-catalog.svc:8181/api/catalog",
    catalog_credential_secret="polaris-spark-credential",
    s3_endpoint="http://rustfs.object-storage.svc:9000",
    s3_secret_name="rustfs-credentials",
)


def _input(**overrides) -> SubmitMaintenanceJobGatewayInput:
    data = {
        "app_name": "tm-run1-compact-1",
        "run_id": "run1",
        "operation": "rewrite_data_files",
        "attempt": 1,
        "catalog": "iceberg",
        "namespace": "sales",
        "table": "orders",
        "where": ["region = 'eu'"],
        "procedure_args": {"min-input-files": 2},
        "callback_url": "http://cp/callback",
    }
    data.update(overrides)
    return SubmitMaintenanceJobGatewayInput(**data)


def test_manifest_snapshot():
    app = build_spark_application(CONFIG, _input())
    assert app["apiVersion"] == "sparkoperator.k8s.io/v1beta2"
    assert app["kind"] == "SparkApplication"
    assert app["metadata"]["name"] == "tm-run1-compact-1"
    assert app["metadata"]["namespace"] == "lakehouse-maintenance-operations"
    assert app["metadata"]["labels"] == {
        "app.kubernetes.io/part-of": "table-maintenance",
        "table-maintenance/run-id": "run1",
        "table-maintenance/operation": "rewrite_data_files",
        "table-maintenance/attempt": "1",
    }
    spec = app["spec"]
    assert spec["image"] == "table-maintenance-spark:dev"
    assert spec["imagePullPolicy"] == "Never"
    assert spec["restartPolicy"] == {"type": "Never"}
    assert spec["sparkVersion"] == "4.0.0"
    assert spec["mainApplicationFile"] == "local:///opt/spark/work-dir/main.py"
    assert spec["deps"]["jars"] == [
        "https://repo1.maven.org/maven2/org/apache/iceberg/"
        "iceberg-spark-runtime-4.0_2.13/1.10.1/iceberg-spark-runtime-4.0_2.13-1.10.1.jar",
        "https://repo1.maven.org/maven2/org/apache/iceberg/"
        "iceberg-aws-bundle/1.10.1/iceberg-aws-bundle-1.10.1.jar",
    ]
    conf = spec["sparkConf"]
    assert conf["spark.sql.session.timeZone"] == "UTC"
    assert conf["spark.sql.extensions"].endswith("IcebergSparkSessionExtensions")
    assert conf["spark.sql.catalog.iceberg"] == "org.apache.iceberg.spark.SparkCatalog"
    assert conf["spark.sql.catalog.iceberg.type"] == "rest"
    assert (
        conf["spark.sql.catalog.iceberg.io-impl"]
        == "org.apache.iceberg.aws.s3.S3FileIO"
    )
    assert "credential" in conf["spark.redaction.regex"]
    assert conf["spark.sql.catalog.iceberg.uri"] == CONFIG.catalog_uri
    assert conf["spark.sql.catalog.iceberg.warehouse"] == "iceberg"
    assert conf["spark.sql.catalog.iceberg.scope"] == "PRINCIPAL_ROLE:ALL"
    assert conf["spark.sql.catalog.iceberg.s3.path-style-access"] == "true"
    assert conf["spark.sql.catalog.iceberg.s3.endpoint"] == CONFIG.s3_endpoint
    assert not any("credential" in key for key in conf)


def test_manifest_driver_and_executor_env():
    spec = build_spark_application(CONFIG, _input())["spec"]
    env = {e["name"]: e for e in spec["driver"]["env"]}
    request = json.loads(env["GLAC_REQUEST"]["value"])
    assert request["app_name"] == "tm-run1-compact-1"
    assert request["where"] == ["region = 'eu'"]
    assert request["callback_url"] == "http://cp/callback"
    assert env["POLARIS_CREDENTIAL"]["valueFrom"]["secretKeyRef"] == {
        "name": "polaris-spark-credential",
        "key": "credential",
    }
    assert env["AWS_REGION"]["value"] == "dummy-region"
    for role in ("driver", "executor"):
        assert spec[role]["envFrom"] == [{"secretRef": {"name": "rustfs-credentials"}}]
        assert "-Divy.cache.dir=/tmp/.ivy2" in spec[role]["javaOptions"]
    assert {"name": "AWS_REGION", "value": "dummy-region"} in spec["executor"]["env"]


def test_app_name_from_domain_helper_fits_k8s_limit():
    for operation in MaintenanceOperation:
        name = spark_application_name("A" * 64, operation, 12)
        assert len(name) <= 63


def test_submit_creates_custom_object():
    api = MagicMock()
    SubmitMaintenanceJobK8sGateway(api, CONFIG).submit(_input())
    kwargs = api.create_namespaced_custom_object.call_args.kwargs
    assert kwargs["group"] == "sparkoperator.k8s.io"
    assert kwargs["plural"] == "sparkapplications"
    assert kwargs["namespace"] == "lakehouse-maintenance-operations"
    assert kwargs["body"]["metadata"]["name"] == "tm-run1-compact-1"


def test_submit_conflict_is_success():
    api = MagicMock()
    api.create_namespaced_custom_object.side_effect = ApiException(status=409)
    SubmitMaintenanceJobK8sGateway(api, CONFIG).submit(_input())
    api.create_namespaced_custom_object.assert_called_once()


def test_submit_other_errors_propagate():
    api = MagicMock()
    api.create_namespaced_custom_object.side_effect = ApiException(status=500)
    with pytest.raises(ApiException):
        SubmitMaintenanceJobK8sGateway(api, CONFIG).submit(_input())


@pytest.mark.parametrize(
    ("status", "expected", "error"),
    [
        (None, "PENDING", None),
        ({}, "PENDING", None),
        ({"applicationState": {"state": ""}}, "PENDING", None),
        ({"applicationState": {"state": "SUBMITTED"}}, "PENDING", None),
        ({"applicationState": {"state": "RUNNING"}}, "RUNNING", None),
        ({"applicationState": {"state": "PENDING_RERUN"}}, "RUNNING", None),
        ({"applicationState": {"state": "INVALIDATING"}}, "RUNNING", None),
        ({"applicationState": {"state": "SUCCEEDING"}}, "RUNNING", None),
        ({"applicationState": {"state": "COMPLETED"}}, "COMPLETED", None),
        (
            {"applicationState": {"state": "FAILED", "errorMessage": "boom"}},
            "FAILED",
            "boom",
        ),
        ({"applicationState": {"state": "SUBMISSION_FAILED"}}, "FAILED", None),
        ({"applicationState": {"state": "FAILING"}}, "FAILED", None),
    ],
)
def test_read_maps_states(status, expected, error):
    api = MagicMock()
    api.get_namespaced_custom_object.return_value = {"status": status}
    out = ReadMaintenanceJobK8sGateway(api, CONFIG).read(
        ReadMaintenanceJobGatewayInput("tm-x")
    )
    assert (out.state, out.error) == (expected, error)


def test_read_missing_status_key_is_pending():
    api = MagicMock()
    api.get_namespaced_custom_object.return_value = {}
    out = ReadMaintenanceJobK8sGateway(api, CONFIG).read(
        ReadMaintenanceJobGatewayInput("tm-x")
    )
    assert out.state == "PENDING"


def test_read_not_found_and_other_errors():
    api = MagicMock()
    gateway = ReadMaintenanceJobK8sGateway(api, CONFIG)
    api.get_namespaced_custom_object.side_effect = ApiException(status=404)
    assert gateway.read(ReadMaintenanceJobGatewayInput("tm-x")).state == "NOT_FOUND"
    api.get_namespaced_custom_object.side_effect = ApiException(status=500)
    with pytest.raises(ApiException):
        gateway.read(ReadMaintenanceJobGatewayInput("tm-x"))


def test_delete_calls_api_and_ignores_not_found():
    api = MagicMock()
    gateway = DeleteMaintenanceJobK8sGateway(api, CONFIG)
    gateway.delete(DeleteMaintenanceJobGatewayInput("tm-x"))
    assert api.delete_namespaced_custom_object.call_args.kwargs["name"] == "tm-x"
    api.delete_namespaced_custom_object.side_effect = ApiException(status=404)
    gateway.delete(DeleteMaintenanceJobGatewayInput("tm-x"))


def test_delete_other_errors_propagate():
    api = MagicMock()
    api.delete_namespaced_custom_object.side_effect = ApiException(status=500)
    with pytest.raises(ApiException):
        DeleteMaintenanceJobK8sGateway(api, CONFIG).delete(
            DeleteMaintenanceJobGatewayInput("tm-x")
        )
