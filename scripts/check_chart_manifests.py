"""Check the wave-25 chart's rendered manifests: Kubernetes schemas, labels and deployment rules.

The chart is rendered once for each of its ci/*-values.yaml scenarios, and each rendering must
pass three checks:

- kubeconform, strict, against the Kubernetes v1.33 schemas and the Gateway API and Volcano CRD
  schemas in platform/25-lakehouse-control-plane/schemas (no network);
- the label standard of check_k8s_labels.py;
- the deployment rules below, which hold for every object the chart renders, whatever its values.

Security: pods run as non-root with seccomp RuntimeDefault; containers drop ALL capabilities and
cannot escalate; only a pod with its own ServiceAccount mounts an API token; service links are
off; every container names an image, requests cpu and memory and limits memory.
Health and wiring: a container that serves a port has readiness and liveness probes on a port it
declares; a Service targets a named port of the pods it selects; an HTTPRoute sends to a port of a
Service in the release and never takes the whole Gateway (every rule matches a path prefix other
than /); a pod that mounts its settings carries their checksum, so it restarts when they change;
every object has a name and every namespaced object its namespace.
Lifecycle and scheduling: a Job ends (Never or OnFailure) and a test pod never restarts; the event
consumer is replaced with Recreate, so two consumers never read the catalog events at once; a
PriorityClass never preempts and is never the cluster default.
Permissions: the Spark Role lets a driver run its executors; a RoleBinding binds a Role of the
release in its own namespace and names its ServiceAccount's namespace.

Usage: check_chart_manifests.py <chart> [--schemas <dir>]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "platform" / "25-lakehouse-control-plane" / "schemas"
KUBERNETES_SCHEMAS = "kubernetes-v1.33.2"
RELEASE = "table-maintenance"
NAMESPACE = "lakehouse-control-plane"

COMPONENT = "app.kubernetes.io/component"
CHECKSUM = "checksum/config"
CLUSTER_SCOPED = {
    "PriorityClass",
    "Queue",
    "ClusterRole",
    "ClusterRoleBinding",
    "Namespace",
    "CustomResourceDefinition",
}
POD_TEMPLATE_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "Job"}
SPARK_DRIVER_RULES = (
    (
        ("pods", "services", "configmaps", "persistentvolumeclaims"),
        ("create", "get", "list", "watch", "update", "patch", "delete", "deletecollection"),
    ),
    (("events",), ("create", "patch")),
)


def _where(doc: dict[str, Any]) -> str:
    return f"{doc.get('kind', '?')}/{(doc.get('metadata') or {}).get('name') or '?'}"


def _namespace(doc: dict[str, Any]) -> str | None:
    return (doc.get("metadata") or {}).get("namespace")


def _component(doc: dict[str, Any]) -> str | None:
    return ((doc.get("metadata") or {}).get("labels") or {}).get(COMPONENT)


def _pod_spec(doc: dict[str, Any]) -> dict[str, Any] | None:
    if doc.get("kind") == "Pod":
        return doc.get("spec") or {}
    if doc.get("kind") in POD_TEMPLATE_KINDS:
        return ((doc.get("spec") or {}).get("template") or {}).get("spec") or {}
    return None


def _pod_labels(doc: dict[str, Any]) -> dict[str, str]:
    if doc.get("kind") == "Pod":
        return (doc.get("metadata") or {}).get("labels") or {}
    return (((doc.get("spec") or {}).get("template") or {}).get("metadata") or {}).get("labels") or {}


def _containers(spec: dict[str, Any]) -> list[dict[str, Any]]:
    return list(spec.get("initContainers") or []) + list(spec.get("containers") or [])


def _pod_violations(doc: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    where = _where(doc)
    violations = []
    security = spec.get("securityContext") or {}
    if not (
        security.get("runAsNonRoot") is True
        and (security.get("runAsUser") or 0) > 0
        and (security.get("runAsGroup") or 0) > 0
        and (security.get("seccompProfile") or {}).get("type") == "RuntimeDefault"
    ):
        violations.append(f"{where}: the pod must run as a non-root user and group with seccomp RuntimeDefault")
    if not spec.get("serviceAccountName") and spec.get("automountServiceAccountToken") is not False:
        violations.append(f"{where}: a pod without its own ServiceAccount must not mount an API token")
    if spec.get("enableServiceLinks") is not False:
        violations.append(f"{where}: the pod must set enableServiceLinks: false")
    if doc["kind"] == "Job" and spec.get("restartPolicy") not in ("Never", "OnFailure"):
        violations.append(f"{where}: restartPolicy must be Never or OnFailure")
    if doc["kind"] == "Pod" and spec.get("restartPolicy") != "Never":
        violations.append(f"{where}: restartPolicy must be Never")
    for container in _containers(spec):
        violations += _container_violations(where, container, doc["kind"] in POD_TEMPLATE_KINDS - {"Job"})
    return violations


def _container_violations(where: str, container: dict[str, Any], long_running: bool) -> list[str]:
    name = container.get("name")
    violations = []
    security = container.get("securityContext") or {}
    if security.get("allowPrivilegeEscalation") is not False or "ALL" not in (
        (security.get("capabilities") or {}).get("drop") or []
    ):
        violations.append(f"{where}: container {name} must not escalate privileges and must drop ALL capabilities")
    if not container.get("image"):
        violations.append(f"{where}: container {name} must name an image")
    resources = container.get("resources") or {}
    requests, limits = resources.get("requests") or {}, resources.get("limits") or {}
    if not (requests.get("cpu") and requests.get("memory") and limits.get("memory")):
        violations.append(f"{where}: container {name} must request cpu and memory and limit memory")
    ports = {port.get("name") for port in container.get("ports") or []}
    for probe in ("readinessProbe", "livenessProbe"):
        if long_running and ports and probe not in container:
            violations.append(f"{where}: container {name} serves a port, so it needs a {probe}")
        handler = (container.get(probe) or {}).get("httpGet") or (container.get(probe) or {}).get("tcpSocket") or {}
        if isinstance(handler.get("port"), str) and handler["port"] not in ports:
            violations.append(
                f"{where}: container {name}'s {probe} names port {handler['port']}, which it does not declare"
            )
    return violations


def _service_violations(doc: dict[str, Any], docs: list[dict[str, Any]]) -> list[str]:
    selector = (doc.get("spec") or {}).get("selector") or {}
    selected = [
        container
        for other in docs
        if _pod_spec(other) is not None
        and _namespace(other) == _namespace(doc)
        and selector
        and selector.items() <= _pod_labels(other).items()
        for container in (_pod_spec(other) or {}).get("containers") or []
    ]
    declared = {port.get("name") for container in selected for port in container.get("ports") or []}
    violations = []
    for port in (doc.get("spec") or {}).get("ports") or []:
        target = port.get("targetPort")
        if not isinstance(target, str):
            violations.append(f"{_where(doc)}: port {port.get('name')} must target a named container port")
        elif target not in declared:
            violations.append(
                f"{_where(doc)}: port {port.get('name')} targets {target}, which no pod it selects declares"
            )
    return violations


def _route_violations(doc: dict[str, Any], docs: list[dict[str, Any]]) -> list[str]:
    exposed = {
        ((other.get("metadata") or {}).get("name"), port.get("port"))
        for other in docs
        if other.get("kind") == "Service" and _namespace(other) == _namespace(doc)
        for port in (other.get("spec") or {}).get("ports") or []
    }
    rules = (doc.get("spec") or {}).get("rules") or []
    whole_gateway = any(
        not rule.get("matches")
        or any(((match.get("path") or {}).get("value") or "/") == "/" for match in rule["matches"])
        for rule in rules
    )
    return [f"{_where(doc)}: every rule must match a path prefix other than /"] * whole_gateway + [
        f"{_where(doc)}: backend {ref.get('name')} port {ref.get('port')} is not a port of a Service in the release"
        for rule in rules
        for ref in rule.get("backendRefs") or []
        if ref.get("kind", "Service") == "Service" and (ref.get("name"), ref.get("port")) not in exposed
    ]


def _checksum_violations(doc: dict[str, Any], spec: dict[str, Any], docs: list[dict[str, Any]]) -> list[str]:
    settings = next(
        (
            volume["configMap"].get("name")
            for volume in spec.get("volumes") or []
            if volume.get("name") == "config" and volume.get("configMap")
        ),
        None,
    )
    if settings is None:
        return []
    config_map = next(
        (
            other
            for other in docs
            if other.get("kind") == "ConfigMap"
            and (other.get("metadata") or {}).get("name") == settings
            and _namespace(other) == _namespace(doc)
        ),
        None,
    )
    annotations = (((doc.get("spec") or {}).get("template") or {}).get("metadata") or {}).get("annotations") or {}
    text = ((config_map or {}).get("data") or {}).get("config.yaml")
    if text is None or annotations.get(CHECKSUM) != hashlib.sha256(text.rstrip("\n").encode()).hexdigest():
        return [f"{_where(doc)}: {CHECKSUM} is not the checksum of ConfigMap {settings}"]
    return []


def _spark_role_violations(doc: dict[str, Any]) -> list[str]:
    granted = {
        (resource, verb)
        for rule in doc.get("rules") or []
        if "" in (rule.get("apiGroups") or [])
        for resource in rule.get("resources") or []
        for verb in rule.get("verbs") or []
    }
    missing = sorted(
        f"{verb} {resource}"
        for resources, verbs in SPARK_DRIVER_RULES
        for resource in resources
        for verb in verbs
        if (resource, verb) not in granted
    )
    return [f"{_where(doc)}: the Spark driver needs {', '.join(missing)}"] if missing else []


def _binding_violations(doc: dict[str, Any], docs: list[dict[str, Any]]) -> list[str]:
    violations = [
        f"{_where(doc)}: ServiceAccount subject {subject.get('name')} must name its namespace"
        for subject in doc.get("subjects") or []
        if subject.get("kind") == "ServiceAccount" and not subject.get("namespace")
    ]
    role = doc.get("roleRef") or {}
    if role.get("kind") == "Role" and not any(
        other.get("kind") == "Role"
        and (other.get("metadata") or {}).get("name") == role.get("name")
        and _namespace(other) == _namespace(doc)
        for other in docs
    ):
        violations.append(
            f"{_where(doc)}: binds Role {role.get('name')}, which the release does not have in {_namespace(doc)}"
        )
    return violations


def _document_violations(doc: dict[str, Any], docs: list[dict[str, Any]]) -> list[str]:
    kind = doc.get("kind")
    where = _where(doc)
    violations = []
    if not (doc.get("metadata") or {}).get("name"):
        violations.append(f"{where}: every object needs a name")
    if kind not in CLUSTER_SCOPED and not _namespace(doc):
        violations.append(f"{where}: a namespaced object must name its namespace")
    spec = _pod_spec(doc)
    if spec is not None:
        violations += _pod_violations(doc, spec)
        if kind == "Deployment":
            violations += _checksum_violations(doc, spec, docs)
    if kind == "Deployment" and _component(doc) == "event-consumer":
        if ((doc.get("spec") or {}).get("strategy") or {}).get("type") != "Recreate":
            violations.append(f"{where}: the event consumer must use the Recreate strategy")
    if kind == "Service":
        violations += _service_violations(doc, docs)
    if kind == "HTTPRoute":
        violations += _route_violations(doc, docs)
    if kind == "PriorityClass":
        if "value" not in doc:
            violations.append(f"{where}: a PriorityClass needs a value")
        if doc.get("preemptionPolicy") != "Never" or doc.get("globalDefault") is not False:
            violations.append(f"{where}: preemptionPolicy must be Never and globalDefault false")
    if kind == "Role" and _component(doc) == "spark-job":
        violations += _spark_role_violations(doc)
    if kind == "RoleBinding":
        violations += _binding_violations(doc, docs)
    return violations


def policy_violations(docs: list[dict[str, Any]]) -> list[str]:
    """Return every deployment rule the rendered objects break, one line each."""
    docs = [doc for doc in docs if doc]
    return [violation for doc in docs for violation in _document_violations(doc, docs)]


def _labels_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "check_k8s_labels", Path(__file__).resolve().parent / "check_k8s_labels.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _kubeconform(rendered: str, schemas: Path) -> list[str]:
    result = subprocess.run(
        [
            "kubeconform",
            "-strict",
            "-summary",
            "-schema-location",
            f"{schemas}/{KUBERNETES_SCHEMAS}/{{{{.ResourceKind}}}}{{{{.KindSuffix}}}}.json",
            "-schema-location",
            f"{schemas}/crds/{{{{.Group}}}}/{{{{.ResourceKind}}}}_{{{{.ResourceAPIVersion}}}}.json",
            "-",
        ],
        input=rendered,
        capture_output=True,
        text=True,
        check=False,
    )
    return [] if result.returncode == 0 else [line for line in result.stdout.splitlines() if line] or [result.stderr]


def main(argv: list[str] | None = None) -> int:
    """Render the chart once per scenario and print every violation; return the exit code."""
    parser = argparse.ArgumentParser(description="Check the wave-25 chart's rendered manifests.")
    parser.add_argument("chart", type=Path)
    parser.add_argument("--schemas", type=Path, default=SCHEMAS)
    args = parser.parse_args(argv)
    labels = _labels_module()
    violations = []
    for values in sorted((args.chart / "ci").glob("*-values.yaml")):
        scenario = f"ci/{values.name}"
        rendered = subprocess.run(
            ["helm", "template", RELEASE, str(args.chart), "--namespace", NAMESPACE, "--values", str(values)],
            capture_output=True,
            text=True,
            check=False,
        )
        if rendered.returncode != 0:
            violations.append(f"{scenario}: helm template failed: {rendered.stderr.strip()}")
            continue
        docs = [doc for doc in yaml.safe_load_all(rendered.stdout) if doc]
        violations += [f"{scenario}: {line}" for line in _kubeconform(rendered.stdout, args.schemas)]
        violations += [f"{scenario}: {line}" for doc in docs for line in labels.check_document(doc, scenario)]
        violations += [f"{scenario}: {line}" for line in policy_violations(docs)]
    for violation in violations:
        print(violation)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
