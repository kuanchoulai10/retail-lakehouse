"""Test the gateway that reads the failure evidence of one maintenance attempt."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from kubernetes.client import (
    V1Container,
    V1ContainerState,
    V1ContainerStateRunning,
    V1ContainerStateTerminated,
    V1ContainerStatus,
    V1ObjectMeta,
    V1Pod,
    V1PodList,
    V1PodSpec,
    V1PodStatus,
)
from kubernetes.client.exceptions import ApiException

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import (
    ReadMaintenanceJobEvidenceK8sGateway,
    SparkK8sConfig,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    JobContainerExit,
    ReadMaintenanceJobEvidenceGatewayInput,
)

CONFIG = SparkK8sConfig(
    image="table-maintenance-spark:dev",
    service_account="spark",
    catalog_uri="http://polaris.lakehouse-catalog.svc:8181/api/catalog",
    catalog_credential_secret="polaris-spark-credential",
    s3_endpoint="http://rustfs.object-storage.svc:9000",
    s3_secret_name="rustfs-credentials",
)
RUN_ID = "mr-01kaa4zc9qf3v8d2m6xk0w7b1n"
RUN_ID_SUFFIX = "01kaa4zc9qf3v8d2m6xk0w7b1n"
INPUT = ReadMaintenanceJobEvidenceGatewayInput(run_id=RUN_ID, operation="rewrite_data_files", attempt=2)


def _terminated(reason: str, exit_code: int, message: str | None = None) -> V1ContainerState:
    return V1ContainerState(terminated=V1ContainerStateTerminated(reason=reason, exit_code=exit_code, message=message))


def _pod(
    name: str,
    role: str,
    *,
    state: V1ContainerState | None = None,
    last_state: V1ContainerState | None = None,
    container: str | None = None,
) -> V1Pod:
    container_name = container or f"spark-kubernetes-{role}"
    return V1Pod(
        metadata=V1ObjectMeta(name=name, labels={"spark-role": role}),
        spec=V1PodSpec(containers=[V1Container(name="istio-proxy"), V1Container(name=container_name)]),
        status=V1PodStatus(
            phase="Failed",
            container_statuses=[
                V1ContainerStatus(
                    name="istio-proxy", image="i", image_id="i", ready=False, restart_count=0, state=None
                ),
                V1ContainerStatus(
                    name=container_name,
                    image="i",
                    image_id="i",
                    ready=False,
                    restart_count=0,
                    state=state,
                    last_state=last_state,
                ),
            ],
        ),
    )


def _gateway(
    application: dict | Exception,
    *pods: V1Pod,
) -> tuple[ReadMaintenanceJobEvidenceK8sGateway, MagicMock, MagicMock]:
    custom = MagicMock(name="custom-objects-api")
    if isinstance(application, Exception):
        custom.get_namespaced_custom_object.side_effect = application
    else:
        custom.get_namespaced_custom_object.return_value = application
    core = MagicMock(name="core-v1-api")
    core.list_namespaced_pod.return_value = V1PodList(items=list(pods))
    return ReadMaintenanceJobEvidenceK8sGateway(custom, core, CONFIG), custom, core


FAILED_APP = {
    "status": {
        "sparkApplicationId": "spark-0123abcd",
        "applicationState": {"state": "FAILED", "errorMessage": "driver container failed with ExitCode: 1"},
    }
}


def test_evidence_reads_the_application_id_and_error():
    """The execution id and job error come from the SparkApplication's status."""
    gateway, custom, _ = _gateway(FAILED_APP)
    out = gateway.read(INPUT)
    assert out.execution_id == "spark-0123abcd"
    assert out.error == "driver container failed with ExitCode: 1"
    assert custom.get_namespaced_custom_object.call_args.kwargs["name"] == f"tm-rdf-{RUN_ID_SUFFIX}-a2"
    assert custom.get_namespaced_custom_object.call_args.kwargs["namespace"] == "lakehouse-maintenance-operations"


def test_evidence_of_a_deleted_application_is_empty_but_lists_pods():
    """A SparkApplication that is gone gives no id and no error; its pods are still read."""
    gateway, _, _ = _gateway(ApiException(status=404), _pod("exec-1", "executor", state=_terminated("OOMKilled", 137)))
    out = gateway.read(INPUT)
    assert (out.execution_id, out.error) == (None, None)
    assert out.containers == (JobContainerExit(role="executor", reason="OOMKilled", exit_code=137, message=None),)


def test_other_api_errors_propagate():
    """An API error other than not found propagates."""
    gateway, _, _ = _gateway(ApiException(status=500))
    with pytest.raises(ApiException):
        gateway.read(INPUT)


def test_evidence_lists_terminated_driver_and_executor_containers():
    """Every terminated Spark container is listed with its role, reason, exit code and message."""
    running = V1ContainerState(running=V1ContainerStateRunning())
    gateway, _, _ = _gateway(
        FAILED_APP,
        _pod("driver", "driver", state=_terminated("Error", 1, "java.lang.OutOfMemoryError: Java heap space")),
        _pod("exec-1", "executor", state=_terminated("OOMKilled", 137)),
        _pod("exec-2", "executor", state=running),
    )
    assert gateway.read(INPUT).containers == (
        JobContainerExit(
            role="driver", reason="Error", exit_code=1, message="java.lang.OutOfMemoryError: Java heap space"
        ),
        JobContainerExit(role="executor", reason="OOMKilled", exit_code=137, message=None),
    )


def test_evidence_reads_last_state_of_a_restarted_container():
    """A container that restarted reports how its previous run terminated."""
    running = V1ContainerState(running=V1ContainerStateRunning())
    gateway, _, _ = _gateway(FAILED_APP, _pod("exec-1", "executor", state=running, last_state=_terminated("Error", 52)))
    assert gateway.read(INPUT).containers == (
        JobContainerExit(role="executor", reason="Error", exit_code=52, message=None),
    )


def test_a_pod_without_a_spark_container_name_reads_its_first_container():
    """A pod whose containers have other names contributes its first container."""
    pod = _pod("exec-1", "executor", state=_terminated("Error", 52), container="other")
    pod.spec.containers = [V1Container(name="other")]
    pod.status.container_statuses = pod.status.container_statuses[1:]
    gateway, _, _ = _gateway(FAILED_APP, pod)
    assert gateway.read(INPUT).containers == (
        JobContainerExit(role="executor", reason="Error", exit_code=52, message=None),
    )


def test_evidence_reports_when_the_driver_started():
    """The driver container's start is read from the pods the evidence already lists."""
    started = datetime(2026, 11, 20, 3, 0, 5, tzinfo=UTC)
    ended = V1ContainerState(terminated=V1ContainerStateTerminated(exit_code=1, started_at=started))
    gateway, _, _ = _gateway(
        FAILED_APP, _pod("driver", "driver", state=ended), _pod("exec-1", "executor", state=_terminated("Error", 52))
    )

    assert gateway.read(INPUT).driver_started_at == started.isoformat()


def test_evidence_without_a_started_driver_has_no_driver_start():
    """An attempt whose driver never started leaves the driver start out."""
    gateway, _, _ = _gateway(FAILED_APP, _pod("exec-1", "executor", state=_terminated("Error", 52)))

    assert gateway.read(INPUT).driver_started_at is None
