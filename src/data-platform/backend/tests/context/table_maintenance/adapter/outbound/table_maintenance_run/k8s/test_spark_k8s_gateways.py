"""Test the gateways that submit, read and delete SparkApplications on Kubernetes."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from kubernetes.client.exceptions import ApiException

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import (
    DeleteMaintenanceJobK8sGateway,
    ReadMaintenanceJobK8sGateway,
    SparkK8sConfig,
    SubmitMaintenanceJobK8sGateway,
    build_spark_application,
    spark_application_name,
)
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    DeleteMaintenanceJobGatewayInput,
    ReadMaintenanceJobGatewayInput,
    SubmitMaintenanceJobGatewayInput,
)

CONFIG = SparkK8sConfig(
    image="table-maintenance-spark:dev",
    service_account="spark",
    catalog_uri="http://polaris.lakehouse-catalog.svc:8181/api/catalog",
    catalog_credential_secret="polaris-spark-credential",
    s3_endpoint="http://rustfs.object-storage.svc:9000",
    s3_secret_name="rustfs-credentials",
)


NAME = spark_application_name("run1", "rewrite_data_files", 1)
ATTEMPT = ("run1", "rewrite_data_files", 1)


def _input(**overrides) -> SubmitMaintenanceJobGatewayInput:
    data = {
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
    """The manifest has the Spark operator API version, kind and application name."""
    app = build_spark_application(CONFIG, _input(), NAME)
    assert app["apiVersion"] == "sparkoperator.k8s.io/v1beta2"
    assert app["kind"] == "SparkApplication"
    assert app["metadata"]["name"] == NAME
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
        "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.10.1/iceberg-aws-bundle-1.10.1.jar",
        "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.4.1/hadoop-aws-3.4.1.jar",
        "https://repo1.maven.org/maven2/software/amazon/awssdk/"
        "s3-transfer-manager/2.33.0/s3-transfer-manager-2.33.0.jar",
    ]
    conf = spec["sparkConf"]
    assert conf["spark.sql.session.timeZone"] == "UTC"
    assert conf["spark.sql.extensions"].endswith("IcebergSparkSessionExtensions")
    assert conf["spark.sql.catalog.iceberg"] == "org.apache.iceberg.spark.SparkCatalog"
    assert conf["spark.sql.catalog.iceberg.type"] == "rest"
    assert conf["spark.sql.catalog.iceberg.io-impl"] == "org.apache.iceberg.aws.s3.S3FileIO"
    assert "credential" in conf["spark.redaction.regex"]
    assert conf["spark.sql.catalog.iceberg.uri"] == CONFIG.catalog_uri
    assert conf["spark.sql.catalog.iceberg.warehouse"] == "iceberg"
    assert conf["spark.sql.catalog.iceberg.scope"] == "PRINCIPAL_ROLE:ALL"
    assert conf["spark.sql.catalog.iceberg.s3.path-style-access"] == "true"
    assert conf["spark.sql.catalog.iceberg.s3.endpoint"] == CONFIG.s3_endpoint
    assert {key for key in conf if "credential" in key} == {"spark.hadoop.fs.s3a.aws.credentials.provider"}


def test_manifest_driver_and_executor_env():
    """The driver request carries the application name, filter and callback URL."""
    spec = build_spark_application(CONFIG, _input(), NAME)["spec"]
    env = {e["name"]: e for e in spec["driver"]["env"]}
    request = json.loads(env["GLAC_REQUEST"]["value"])
    assert request["app_name"] == NAME
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


def test_application_name_fits_k8s_limit():
    """The application name fits the 63 character Kubernetes limit."""
    for operation in MaintenanceOperation:
        name = spark_application_name("A" * 64, operation.value, 12)
        assert len(name) <= 63


def test_submit_creates_custom_object():
    """Submitting creates a SparkApplication custom object in the maintenance namespace."""
    api = MagicMock()
    output = SubmitMaintenanceJobK8sGateway(api, CONFIG).submit(_input())
    kwargs = api.create_namespaced_custom_object.call_args.kwargs
    assert kwargs["group"] == "sparkoperator.k8s.io"
    assert kwargs["plural"] == "sparkapplications"
    assert kwargs["namespace"] == "lakehouse-maintenance-operations"
    assert kwargs["body"]["metadata"]["name"] == spark_application_name(*ATTEMPT)
    assert output.job_name == spark_application_name(*ATTEMPT)


def test_submit_conflict_is_success():
    """Submitting an application that already exists counts as success."""
    api = MagicMock()
    api.create_namespaced_custom_object.side_effect = ApiException(status=409)
    output = SubmitMaintenanceJobK8sGateway(api, CONFIG).submit(_input())
    api.create_namespaced_custom_object.assert_called_once()
    assert output.job_name == NAME


def test_submit_other_errors_propagate():
    """Other API errors from a submit are raised."""
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
    """Each SparkApplication state maps to a job state and error."""
    api = MagicMock()
    api.get_namespaced_custom_object.return_value = {"status": status}
    out = ReadMaintenanceJobK8sGateway(api, CONFIG).read(ReadMaintenanceJobGatewayInput(*ATTEMPT))
    assert (out.state, out.error) == (expected, error)


def test_read_missing_status_key_is_pending():
    """An application with no status yet reads as pending."""
    api = MagicMock()
    api.get_namespaced_custom_object.return_value = {}
    out = ReadMaintenanceJobK8sGateway(api, CONFIG).read(ReadMaintenanceJobGatewayInput(*ATTEMPT))
    assert out.state == "PENDING"


def test_read_looks_up_the_application_named_after_the_attempt():
    """Reading looks up the application named after the run, operation and attempt."""
    api = MagicMock()
    api.get_namespaced_custom_object.return_value = {}
    ReadMaintenanceJobK8sGateway(api, CONFIG).read(ReadMaintenanceJobGatewayInput(*ATTEMPT))
    assert api.get_namespaced_custom_object.call_args.kwargs["name"] == NAME


def test_read_not_found_and_other_errors():
    """A missing application reads as NOT_FOUND and other API errors are raised."""
    api = MagicMock()
    gateway = ReadMaintenanceJobK8sGateway(api, CONFIG)
    api.get_namespaced_custom_object.side_effect = ApiException(status=404)
    assert gateway.read(ReadMaintenanceJobGatewayInput(*ATTEMPT)).state == "NOT_FOUND"
    api.get_namespaced_custom_object.side_effect = ApiException(status=500)
    with pytest.raises(ApiException):
        gateway.read(ReadMaintenanceJobGatewayInput(*ATTEMPT))


def test_delete_calls_api_and_ignores_not_found():
    """Deleting calls the API for the named application and ignores a missing one."""
    api = MagicMock()
    gateway = DeleteMaintenanceJobK8sGateway(api, CONFIG)
    gateway.delete(DeleteMaintenanceJobGatewayInput(*ATTEMPT))
    assert api.delete_namespaced_custom_object.call_args.kwargs["name"] == NAME
    api.delete_namespaced_custom_object.side_effect = ApiException(status=404)
    gateway.delete(DeleteMaintenanceJobGatewayInput(*ATTEMPT))


def test_delete_other_errors_propagate():
    """Other API errors from a delete are raised."""
    api = MagicMock()
    api.delete_namespaced_custom_object.side_effect = ApiException(status=500)
    with pytest.raises(ApiException):
        DeleteMaintenanceJobK8sGateway(api, CONFIG).delete(DeleteMaintenanceJobGatewayInput(*ATTEMPT))
