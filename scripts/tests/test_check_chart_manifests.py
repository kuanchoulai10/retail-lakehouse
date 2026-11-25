"""Test the deployment rules the wave-25 chart's rendered manifests keep."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "check_chart_manifests", Path(__file__).resolve().parents[1] / "check_chart_manifests.py"
)
assert _SPEC and _SPEC.loader
check_chart_manifests = importlib.util.module_from_spec(_SPEC)
sys.modules["check_chart_manifests"] = check_chart_manifests
_SPEC.loader.exec_module(check_chart_manifests)
policy_violations = check_chart_manifests.policy_violations

NS = "control-plane"
JOBS = "jobs"
SETTINGS = "log_level: INFO\n"
POD_SECURITY = {
    "runAsNonRoot": True,
    "runAsUser": 10001,
    "runAsGroup": 10001,
    "seccompProfile": {"type": "RuntimeDefault"},
}
CONTAINER_SECURITY = {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}}
RESOURCES = {"requests": {"cpu": "10m", "memory": "64Mi"}, "limits": {"memory": "128Mi"}}
PROBE = {"httpGet": {"path": "/healthz", "port": "http"}}


def _container(name: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "image": "app:1", "securityContext": CONTAINER_SECURITY, "resources": RESOURCES, **extra}


def _pod_spec(*containers: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "enableServiceLinks": False,
        "automountServiceAccountToken": False,
        "securityContext": POD_SECURITY,
        "containers": list(containers),
        **extra,
    }


def _meta(name: str, namespace: str | None = NS, **extra: Any) -> dict[str, Any]:
    return {"name": name, **({"namespace": namespace} if namespace else {}), **extra}


def _manifests() -> list[dict[str, Any]]:
    """A small release that keeps every rule."""
    api_labels = {"app.kubernetes.io/component": "api"}
    return [
        {"apiVersion": "v1", "kind": "ConfigMap", "metadata": _meta("api-config"), "data": {"config.yaml": SETTINGS}},
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": _meta("api", labels=api_labels),
            "spec": {
                "selector": {"matchLabels": api_labels},
                "template": {
                    "metadata": {
                        "labels": api_labels,
                        "annotations": {"checksum/config": hashlib.sha256(SETTINGS.rstrip("\n").encode()).hexdigest()},
                    },
                    "spec": _pod_spec(
                        _container(
                            "api",
                            ports=[{"name": "http", "containerPort": 8000}],
                            readinessProbe=PROBE,
                            livenessProbe=PROBE,
                        ),
                        initContainers=[_container("wait")],
                        volumes=[{"name": "config", "configMap": {"name": "api-config"}}],
                    ),
                },
            },
        },
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": _meta("consumer", labels={"app.kubernetes.io/component": "event-consumer"}),
            "spec": {
                "strategy": {"type": "Recreate"},
                "template": {
                    "spec": _pod_spec(
                        _container("consumer"),
                        serviceAccountName="consumer",
                        automountServiceAccountToken=True,
                    )
                },
            },
        },
        {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": _meta("api"),
            "spec": {"selector": api_labels, "ports": [{"name": "http", "port": 80, "targetPort": "http"}]},
        },
        {
            "apiVersion": "gateway.networking.k8s.io/v1",
            "kind": "HTTPRoute",
            "metadata": _meta("api"),
            "spec": {
                "rules": [
                    {
                        "matches": [{"path": {"type": "PathPrefix", "value": "/api"}}],
                        "backendRefs": [{"name": "api", "port": 80}],
                    }
                ]
            },
        },
        {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": _meta("migrate"),
            "spec": {"template": {"spec": _pod_spec(_container("migrate"), restartPolicy="OnFailure")}},
        },
        {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": _meta("test"),
            "spec": _pod_spec(_container("test"), restartPolicy="Never"),
        },
        {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "Role",
            "metadata": _meta("spark", JOBS, labels={"app.kubernetes.io/component": "spark-job"}),
            "rules": [
                {
                    "apiGroups": [""],
                    "resources": ["pods", "services", "configmaps", "persistentvolumeclaims"],
                    "verbs": ["create", "get", "list", "watch", "update", "patch", "delete", "deletecollection"],
                },
                {"apiGroups": [""], "resources": ["events"], "verbs": ["create", "patch"]},
            ],
        },
        {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "RoleBinding",
            "metadata": _meta("spark", JOBS),
            "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": "spark"},
            "subjects": [{"kind": "ServiceAccount", "name": "spark", "namespace": JOBS}],
        },
        {
            "apiVersion": "scheduling.k8s.io/v1",
            "kind": "PriorityClass",
            "metadata": _meta("p0", None),
            "value": 1000003,
            "preemptionPolicy": "Never",
            "globalDefault": False,
        },
        {"apiVersion": "scheduling.volcano.sh/v1beta1", "kind": "Queue", "metadata": _meta("queue", None)},
    ]


def _find(docs: list[dict[str, Any]], kind: str, name: str) -> dict[str, Any]:
    return next(d for d in docs if d["kind"] == kind and d["metadata"]["name"] == name)


def _api_pod(docs: list[dict[str, Any]]) -> dict[str, Any]:
    return _find(docs, "Deployment", "api")["spec"]["template"]["spec"]


def _broken(change) -> list[str]:
    docs = copy.deepcopy(_manifests())
    change(docs)
    return policy_violations(docs)


def test_a_release_that_keeps_every_rule_has_no_violation():
    """A release that keeps every rule has no violation."""
    assert policy_violations(_manifests()) == []


@pytest.mark.parametrize(
    ("field", "value"),
    [("runAsNonRoot", False), ("runAsUser", 0), ("runAsGroup", None), ("seccompProfile", {"type": "Unconfined"})],
)
def test_every_pod_runs_as_a_user_that_is_not_root_under_the_default_seccomp_profile(field: str, value: Any):
    """Every pod runs as a user that is not root under the default seccomp profile."""

    def change(docs):
        security = dict(POD_SECURITY)
        if value is None:
            del security[field]
        else:
            security[field] = value
        _find(docs, "Job", "migrate")["spec"]["template"]["spec"]["securityContext"] = security

    assert _broken(change) == ["Job/migrate: the pod must run as a non-root user and group with seccomp RuntimeDefault"]


def test_a_bare_pod_is_held_to_the_same_rules():
    """A bare pod is held to the same rules."""

    def change(docs):
        del _find(docs, "Pod", "test")["spec"]["securityContext"]

    assert _broken(change) == ["Pod/test: the pod must run as a non-root user and group with seccomp RuntimeDefault"]


@pytest.mark.parametrize(
    "security",
    [
        {"capabilities": {"drop": ["ALL"]}},
        {"allowPrivilegeEscalation": False},
        {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["NET_RAW"]}},
    ],
)
def test_every_container_drops_all_capabilities_and_cannot_escalate(security: dict[str, Any]):
    """Every container drops all capabilities and cannot escalate."""

    def change(docs):
        _api_pod(docs)["initContainers"][0]["securityContext"] = security

    assert _broken(change) == [
        "Deployment/api: container wait must not escalate privileges and must drop ALL capabilities"
    ]


def test_a_pod_without_its_own_service_account_mounts_no_api_token():
    """A pod without its own service account mounts no api token."""

    def change(docs):
        _api_pod(docs)["automountServiceAccountToken"] = True

    assert _broken(change) == ["Deployment/api: a pod without its own ServiceAccount must not mount an API token"]


def test_every_pod_turns_off_service_links():
    """Every pod turns off service links."""

    def change(docs):
        del _find(docs, "Pod", "test")["spec"]["enableServiceLinks"]

    assert _broken(change) == ["Pod/test: the pod must set enableServiceLinks: false"]


@pytest.mark.parametrize(
    "resources",
    [
        {"limits": {"memory": "1Gi"}},
        {"requests": {"cpu": "1"}, "limits": {"memory": "1Gi"}},
        {"requests": {"cpu": "1", "memory": "1Gi"}},
    ],
)
def test_every_container_requests_cpu_and_memory_and_limits_memory(resources: dict[str, Any]):
    """Every container requests cpu and memory and limits memory."""

    def change(docs):
        _api_pod(docs)["initContainers"][0]["resources"] = resources

    assert _broken(change) == ["Deployment/api: container wait must request cpu and memory and limit memory"]


def test_every_container_names_an_image():
    """Every container names an image."""

    def change(docs):
        del _find(docs, "Job", "migrate")["spec"]["template"]["spec"]["containers"][0]["image"]

    assert _broken(change) == ["Job/migrate: container migrate must name an image"]


@pytest.mark.parametrize("probe", ["readinessProbe", "livenessProbe"])
def test_a_container_that_serves_a_port_has_both_probes(probe: str):
    """A container that serves a port has both probes."""

    def change(docs):
        del _api_pod(docs)["containers"][0][probe]

    assert _broken(change) == [f"Deployment/api: container api serves a port, so it needs a {probe}"]


def test_a_probe_names_a_port_its_container_declares():
    """A probe names a port its container declares."""

    def change(docs):
        _api_pod(docs)["containers"][0]["livenessProbe"] = {"httpGet": {"path": "/healthz", "port": "web"}}

    assert _broken(change) == [
        "Deployment/api: container api's livenessProbe names port web, which it does not declare"
    ]


def test_a_service_targets_a_named_port_of_the_pods_it_selects():
    """A service targets a named port of the pods it selects."""

    def change(docs):
        _find(docs, "Service", "api")["spec"]["ports"][0]["targetPort"] = "web"

    assert _broken(change) == ["Service/api: port http targets web, which no pod it selects declares"]


def test_a_service_names_its_target_port():
    """A service names its target port."""

    def change(docs):
        del _find(docs, "Service", "api")["spec"]["ports"][0]["targetPort"]

    assert _broken(change) == ["Service/api: port http must target a named container port"]


def test_a_service_selects_pods_of_the_release():
    """A service selects pods of the release."""

    def change(docs):
        _find(docs, "Service", "api")["spec"]["selector"] = {"app.kubernetes.io/component": "nothing"}

    assert _broken(change) == ["Service/api: port http targets http, which no pod it selects declares"]


@pytest.mark.parametrize(("backend", "port"), [("missing", 80), ("api", 81), ("api", None)])
def test_a_route_sends_to_a_port_a_service_of_the_release_exposes(backend: str, port: int | None):
    """A route sends to a port a service of the release exposes."""

    def change(docs):
        ref = {"name": backend, **({"port": port} if port else {})}
        _find(docs, "HTTPRoute", "api")["spec"]["rules"][0]["backendRefs"] = [ref]

    assert _broken(change) == [
        f"HTTPRoute/api: backend {backend} port {port} is not a port of a Service in the release"
    ]


@pytest.mark.parametrize(
    ("kind", "name", "policy"), [("Job", "migrate", None), ("Job", "migrate", "Always"), ("Pod", "test", "OnFailure")]
)
def test_a_job_or_a_test_pod_ends_instead_of_restarting_forever(kind: str, name: str, policy: str | None):
    """A job or a test pod ends instead of restarting forever."""

    def change(docs):
        doc = _find(docs, kind, name)
        spec = doc["spec"]["template"]["spec"] if kind == "Job" else doc["spec"]
        if policy is None:
            del spec["restartPolicy"]
        else:
            spec["restartPolicy"] = policy

    allowed = "Never or OnFailure" if kind == "Job" else "Never"
    assert _broken(change) == [f"{kind}/{name}: restartPolicy must be {allowed}"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("preemptionPolicy", None),
        ("preemptionPolicy", "PreemptLowerPriority"),
        ("globalDefault", True),
        ("globalDefault", None),
    ],
)
def test_a_priority_class_never_preempts_and_is_never_the_cluster_default(field: str, value: Any):
    """A priority class never preempts and is never the cluster default."""

    def change(docs):
        doc = _find(docs, "PriorityClass", "p0")
        if value is None:
            del doc[field]
        else:
            doc[field] = value

    assert _broken(change) == ["PriorityClass/p0: preemptionPolicy must be Never and globalDefault false"]


def test_a_priority_class_has_a_value():
    """A priority class has a value."""

    def change(docs):
        del _find(docs, "PriorityClass", "p0")["value"]

    assert _broken(change) == ["PriorityClass/p0: a PriorityClass needs a value"]


@pytest.mark.parametrize("strategy", [None, {"type": "RollingUpdate"}])
def test_the_event_consumer_is_stopped_before_its_replacement_starts(strategy: dict[str, Any] | None):
    """The event consumer is stopped before its replacement starts."""

    def change(docs):
        spec = _find(docs, "Deployment", "consumer")["spec"]
        if strategy is None:
            del spec["strategy"]
        else:
            spec["strategy"] = strategy

    assert _broken(change) == ["Deployment/consumer: the event consumer must use the Recreate strategy"]


@pytest.mark.parametrize(("rule", "item"), [(0, "resources"), (0, "verbs"), (1, "resources"), (1, "verbs")])
def test_the_spark_role_grants_what_a_driver_needs_to_run_its_executors(rule: int, item: str):
    """The spark role grants what a driver needs to run its executors."""

    def change(docs):
        _find(docs, "Role", "spark")["rules"][rule][item] = _find(docs, "Role", "spark")["rules"][rule][item][1:]

    [violation] = _broken(change)
    assert violation.startswith("Role/spark: the Spark driver needs ")


def test_a_role_binding_names_its_service_account_s_namespace():
    """A role binding names its service account's namespace."""

    def change(docs):
        del _find(docs, "RoleBinding", "spark")["subjects"][0]["namespace"]

    assert _broken(change) == ["RoleBinding/spark: ServiceAccount subject spark must name its namespace"]


def test_a_role_binding_points_at_a_role_of_the_release_in_its_namespace():
    """A role binding points at a role of the release in its namespace."""

    def change(docs):
        _find(docs, "RoleBinding", "spark")["roleRef"]["name"] = "other"

    assert _broken(change) == ["RoleBinding/spark: binds Role other, which the release does not have in jobs"]


def test_every_object_has_a_name():
    """Every object has a name."""

    def change(docs):
        del _find(docs, "Role", "spark")["metadata"]["name"]

    assert "Role/?: every object needs a name" in _broken(change)


@pytest.mark.parametrize(("kind", "name"), [("Service", "api"), ("RoleBinding", "spark"), ("ConfigMap", "api-config")])
def test_every_namespaced_object_names_its_namespace(kind: str, name: str):
    """Every namespaced object names its namespace."""

    def change(docs):
        del _find(docs, kind, name)["metadata"]["namespace"]

    assert f"{kind}/{name}: a namespaced object must name its namespace" in _broken(change)


def test_a_pod_restarts_when_its_settings_change():
    """A pod restarts when its settings change."""

    def change(docs):
        _find(docs, "ConfigMap", "api-config")["data"]["config.yaml"] = "log_level: DEBUG\n"

    assert _broken(change) == ["Deployment/api: checksum/config is not the checksum of ConfigMap api-config"]


def test_a_pod_that_mounts_settings_carries_their_checksum():
    """A pod that mounts settings carries their checksum."""

    def change(docs):
        del _find(docs, "Deployment", "api")["spec"]["template"]["metadata"]["annotations"]

    assert _broken(change) == ["Deployment/api: checksum/config is not the checksum of ConfigMap api-config"]


@pytest.mark.parametrize("path", [{"type": "PathPrefix"}, {"type": "PathPrefix", "value": "/"}, None])
def test_a_route_never_takes_the_whole_gateway(path: dict[str, Any] | None):
    """A match without a path, or on /, would send every request the Gateway gets to this release."""

    def change(docs):
        _find(docs, "HTTPRoute", "api")["spec"]["rules"][0]["matches"] = [{"path": path}] if path else []

    assert _broken(change) == ["HTTPRoute/api: every rule must match a path prefix other than /"]
