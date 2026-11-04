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
SELECTOR = {
    "app.kubernetes.io/name": "postgres",
    "app.kubernetes.io/instance": "polaris-db",
}


def deployment(labels=None, selector=None, pod_labels=None):
    """Build a Deployment, defaulting every label block to the valid set."""
    return {
        "kind": "Deployment",
        "metadata": {"name": "polaris-db", "labels": dict(LABELS if labels is None else labels)},
        "spec": {
            "selector": {"matchLabels": dict(SELECTOR if selector is None else selector)},
            "template": {"metadata": {"labels": dict(LABELS if pod_labels is None else pod_labels)}},
        },
    }


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
    pod = {**LABELS, "app.kubernetes.io/component": "cache"}
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
