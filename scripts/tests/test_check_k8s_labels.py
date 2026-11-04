"""Test the Kubernetes label standard checker."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "check_k8s_labels", Path(__file__).resolve().parents[1] / "check_k8s_labels.py"
)
assert _SPEC and _SPEC.loader
check_k8s_labels = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_k8s_labels)
check_document = check_k8s_labels.check_document

LABELS = {
    "app.kubernetes.io/name": "postgres",
    "app.kubernetes.io/instance": "polaris-db",
    "app.kubernetes.io/component": "database",
    "app.kubernetes.io/part-of": "polaris",
    "app.kubernetes.io/managed-by": "kubectl",
}
VERSION = "app.kubernetes.io/version"
POD_LABELS = {**LABELS, VERSION: "17-alpine"}
CONTAINERS = [{"name": "postgres", "image": "postgres:17-alpine"}]
SELECTOR = {
    "app.kubernetes.io/name": "postgres",
    "app.kubernetes.io/instance": "polaris-db",
}


def deployment(labels=None, selector=None, pod_labels=None, containers=None):
    """Build a Deployment, defaulting every label block and container to the valid set."""
    return {
        "kind": "Deployment",
        "metadata": {"name": "polaris-db", "labels": dict(LABELS if labels is None else labels)},
        "spec": {
            "selector": {"matchLabels": dict(SELECTOR if selector is None else selector)},
            "template": {
                "metadata": {"labels": dict(POD_LABELS if pod_labels is None else pod_labels)},
                "spec": {"containers": CONTAINERS if containers is None else containers},
            },
        },
    }


def strimzi(kind, version, pod_labels, path):
    """Build a Strimzi custom resource whose pod template sits at path under spec."""
    template = {"pod": {"metadata": {"labels": pod_labels}}} if pod_labels is not None else {}
    spec = {"version": version, "template": template}
    for key in reversed(path):
        spec = {key: spec}
    return {"kind": kind, "metadata": {"name": "k", "labels": dict(LABELS)}, "spec": spec}


def test_valid_deployment_has_no_violations():
    """A Deployment that follows the standard passes."""
    assert check_document(deployment(), "f.yaml") == []


def test_missing_required_label_is_reported():
    """Each missing recommended label is reported."""
    labels = {k: v for k, v in LABELS.items() if k != "app.kubernetes.io/part-of"}
    violations = check_document({"kind": "Secret", "metadata": {"name": "s", "labels": labels}}, "f.yaml")
    assert violations == ["f.yaml: Secret/s metadata.labels is missing app.kubernetes.io/part-of"]


def test_object_without_labels_reports_every_required_label():
    """An object with no labels misses all four."""
    violations = check_document({"kind": "ConfigMap", "metadata": {"name": "c"}}, "f.yaml")
    assert len(violations) == 4


def test_unprefixed_label_key_is_reported():
    """The bare app label is rejected."""
    violations = check_document(deployment(labels={**LABELS, "app": "polaris-db"}), "f.yaml")
    assert violations == ["f.yaml: Deployment/polaris-db metadata.labels uses unprefixed key 'app'"]


def test_pod_template_must_carry_the_same_recommended_labels():
    """Pod template values must equal the object's."""
    pod = {**POD_LABELS, "app.kubernetes.io/component": "cache"}
    violations = check_document(deployment(pod_labels=pod), "f.yaml")
    assert violations == [
        "f.yaml: Deployment/polaris-db pod template label app.kubernetes.io/component "
        "is 'cache', metadata has 'database'"
    ]


def test_selector_with_part_of_is_reported():
    """part-of is not allowed in a selector."""
    violations = check_document(deployment(selector={**SELECTOR, "app.kubernetes.io/part-of": "polaris"}), "f.yaml")
    assert violations == [
        "f.yaml: Deployment/polaris-db selector may only use app.kubernetes.io/name, "
        "app.kubernetes.io/instance, app.kubernetes.io/component (found app.kubernetes.io/part-of)"
    ]


def test_selector_without_instance_is_reported():
    """A selector must include instance."""
    violations = check_document(deployment(selector={"app.kubernetes.io/name": "postgres"}), "f.yaml")
    assert violations == ["f.yaml: Deployment/polaris-db selector is missing app.kubernetes.io/instance"]


def test_selector_must_match_pod_template():
    """A selector value must match the pod template."""
    violations = check_document(deployment(selector={**SELECTOR, "app.kubernetes.io/instance": "other"}), "f.yaml")
    assert violations == [
        "f.yaml: Deployment/polaris-db selector app.kubernetes.io/instance=other does not match the pod template"
    ]


def test_service_selector_follows_the_same_rule():
    """Service selectors follow the workload selector rule."""
    service = {
        "kind": "Service",
        "metadata": {"name": "polaris-db", "labels": dict(LABELS)},
        "spec": {"selector": {"app": "polaris-db"}},
    }
    violations = check_document(service, "f.yaml")
    assert "f.yaml: Service/polaris-db selector is missing app.kubernetes.io/name" in violations


def test_service_without_selector_is_fine():
    """A Service without a selector is not checked."""
    service = {"kind": "Service", "metadata": {"name": "ext", "labels": dict(LABELS)}, "spec": {}}
    assert check_document(service, "f.yaml") == []


def test_job_pod_template_is_checked_without_selector():
    """Job pod templates are checked; Jobs have no selector."""
    job = {
        "kind": "Job",
        "metadata": {"name": "j", "labels": dict(LABELS)},
        "spec": {"template": {"metadata": {"labels": {"app": "j"}}}},
    }
    violations = check_document(job, "f.yaml")
    assert "f.yaml: Job/j pod template labels uses unprefixed key 'app'" in violations


def test_document_without_kind_is_ignored():
    """A YAML document without kind is ignored."""
    assert check_document({"foo": "bar"}, "f.yaml") == []


def test_pod_template_without_version_is_reported():
    """Workload pod templates must carry app.kubernetes.io/version."""
    violations = check_document(deployment(pod_labels=dict(LABELS)), "f.yaml")
    assert violations == ["f.yaml: Deployment/polaris-db pod template labels is missing app.kubernetes.io/version"]


def test_version_must_match_a_container_image_tag():
    """The version label is the tag of one of the pod's containers."""
    violations = check_document(deployment(pod_labels={**LABELS, VERSION: "16"}), "f.yaml")
    assert violations == [
        "f.yaml: Deployment/polaris-db pod template app.kubernetes.io/version '16' "
        "is not the tag of any container image (17-alpine)"
    ]


def test_version_matches_any_container_but_not_an_init_container():
    """A sidecar's tag counts; an init container's does not."""
    containers = [{"name": "mc", "image": "pgsty/mc:R1"}, {"name": "aws", "image": "amazon/aws-cli:2.38.1"}]
    assert check_document(deployment(pod_labels={**LABELS, VERSION: "2.38.1"}, containers=containers), "f.yaml") == []
    job = deployment(pod_labels={**LABELS, VERSION: "1.37.0"})
    job["spec"]["template"]["spec"]["initContainers"] = [{"name": "init", "image": "busybox:1.37.0"}]
    assert "is not the tag of any container image" in check_document(job, "f.yaml")[0]


def test_strimzi_kafka_pod_version_must_match_kafka_version():
    """Kafka broker pods carry spec.kafka.version as their version label."""
    good = strimzi("Kafka", "4.0.0", {"version": "4.0.0"}, ["kafka"])
    assert check_document(good, "f.yaml") == []
    bad = strimzi("Kafka", "4.0.0", {"version": "3.9.0"}, ["kafka"])
    assert check_document(bad, "f.yaml") == [
        "f.yaml: Kafka/k pod template version '3.9.0' is not spec.kafka.version '4.0.0'"
    ]


def test_strimzi_pod_version_uses_the_plain_version_key():
    """Strimzi strips app.kubernetes.io/* from pod templates, so the prefixed key does not count."""
    violations = check_document(strimzi("KafkaConnect", "4.0.0", {VERSION: "4.0.0"}, []), "f.yaml")
    assert violations == ["f.yaml: KafkaConnect/k pod template labels is missing version"]


def test_strimzi_connect_without_pod_version_is_reported():
    """KafkaConnect pods carry spec.version as their version label."""
    violations = check_document(strimzi("KafkaConnect", "4.0.0", None, []), "f.yaml")
    assert violations == ["f.yaml: KafkaConnect/k pod template labels is missing version"]
