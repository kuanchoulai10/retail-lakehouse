"""Test the gateway that reads the live pods of one maintenance attempt."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, call

import pytest
from kubernetes.client import (
    V1ContainerState,
    V1ContainerStateRunning,
    V1ContainerStatus,
    V1ObjectMeta,
    V1Pod,
    V1PodList,
    V1PodStatus,
)
from kubernetes.client.exceptions import ApiException

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import (
    ReadMaintenanceJobPodsK8sGateway,
    SparkK8sConfig,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ReadMaintenanceJobPodsGatewayInput,
    ReadMaintenanceJobPodsGatewayOutput,
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
INPUT = ReadMaintenanceJobPodsGatewayInput(run_id=RUN_ID, operation="rewrite_data_files", attempt=2)


def _pod(name: str, phase: str | None, *, deleting: bool = False) -> V1Pod:
    deletion_timestamp = datetime(2026, 11, 13, tzinfo=UTC) if deleting else None
    return V1Pod(
        metadata=V1ObjectMeta(name=name, deletion_timestamp=deletion_timestamp),
        status=V1PodStatus(phase=phase),
    )


OUR_SELECTOR = (
    f"table-maintenance/run-id={RUN_ID},table-maintenance/operation=rewrite_data_files,table-maintenance/attempt=2"
)
OPERATOR_SELECTOR = f"sparkoperator.k8s.io/app-name=tm-rdf-{RUN_ID_SUFFIX}-a2"


def _gateway(*pods: V1Pod, by_operator: tuple[V1Pod, ...] = ()) -> tuple[ReadMaintenanceJobPodsK8sGateway, MagicMock]:
    api = MagicMock(name="core-v1-api")

    def list_pods(namespace: str, label_selector: str) -> V1PodList:
        return V1PodList(items=list(by_operator if label_selector == OPERATOR_SELECTOR else pods))

    api.list_namespaced_pod.side_effect = list_pods
    return ReadMaintenanceJobPodsK8sGateway(api, CONFIG), api


def test_read_pods_selects_the_attempt_by_its_labels_and_by_its_application():
    """The pods are listed in the Spark namespace by the attempt labels and by the operator's application label."""
    gateway, api = _gateway()

    gateway.read(INPUT)

    assert api.list_namespaced_pod.call_args_list == [
        call(namespace="lakehouse-maintenance-operations", label_selector=OUR_SELECTOR),
        call(namespace="lakehouse-maintenance-operations", label_selector=OPERATOR_SELECTOR),
    ]


def test_read_pods_finds_pods_that_carry_only_the_operator_label():
    """A pod of an attempt submitted before the attempt labels existed is found by its application label."""
    gateway, _ = _gateway(_pod("driver", "Running"), by_operator=(_pod("driver", "Running"), _pod("exec-1", "Pending")))

    assert gateway.read(INPUT).live_pods == ("driver", "exec-1")


def test_read_pods_counts_pending_running_and_unknown_as_live():
    """Pending, running and unknown pods are live; succeeded and failed pods are not."""
    gateway, _ = _gateway(
        _pod("driver", "Pending"),
        _pod("exec-1", "Running"),
        _pod("exec-2", "Unknown"),
        _pod("exec-3", "Succeeded"),
        _pod("exec-4", "Failed"),
    )

    assert gateway.read(INPUT) == ReadMaintenanceJobPodsGatewayOutput(live_pods=("driver", "exec-1", "exec-2"))


def test_read_pods_counts_a_terminating_running_pod_as_live():
    """A running pod that is being deleted can still write, so it is live."""
    gateway, _ = _gateway(_pod("driver", "Running", deleting=True))

    assert gateway.read(INPUT).live_pods == ("driver",)


def test_read_pods_counts_a_pod_without_a_phase_as_live():
    """A pod whose phase is not reported yet is live."""
    gateway, _ = _gateway(_pod("driver", None))

    assert gateway.read(INPUT).live_pods == ("driver",)


def test_read_pods_with_no_pod_is_empty():
    """No pod with the attempt's labels means no live pod."""
    gateway, _ = _gateway()

    assert gateway.read(INPUT).live_pods == ()


def test_read_pods_propagates_api_errors():
    """An API error propagates so the caller retries."""
    api = MagicMock(name="core-v1-api")
    api.list_namespaced_pod.side_effect = ApiException(status=500)

    with pytest.raises(ApiException):
        ReadMaintenanceJobPodsK8sGateway(api, CONFIG).read(INPUT)


def test_read_pods_reports_when_the_driver_started():
    """The driver container's start is read from the attempt's driver pod."""
    started = datetime(2026, 11, 20, 3, 0, 5, tzinfo=UTC)
    driver = V1Pod(
        metadata=V1ObjectMeta(name="driver", labels={"spark-role": "driver"}),
        status=V1PodStatus(
            phase="Running",
            container_statuses=[
                V1ContainerStatus(
                    name="spark-kubernetes-driver",
                    image="i",
                    image_id="i",
                    ready=True,
                    restart_count=0,
                    state=V1ContainerState(running=V1ContainerStateRunning(started_at=started)),
                )
            ],
        ),
    )
    gateway, _ = _gateway(driver)

    assert gateway.read(INPUT).driver_started_at == started.isoformat()


def test_read_pods_without_a_started_driver_has_no_driver_start():
    """A driver that has not started leaves the driver start out."""
    gateway, _ = _gateway(_pod("driver", "Pending"))

    assert gateway.read(INPUT).driver_started_at is None
