"""Test the converter from a CustomResourceDefinition to the JSON schemas kubeconform reads."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

_SPEC = importlib.util.spec_from_file_location(
    "crd_json_schemas", Path(__file__).resolve().parents[1] / "crd_json_schemas.py"
)
assert _SPEC and _SPEC.loader
crd_json_schemas = importlib.util.module_from_spec(_SPEC)
sys.modules["crd_json_schemas"] = crd_json_schemas
_SPEC.loader.exec_module(crd_json_schemas)

CRD = {
    "apiVersion": "apiextensions.k8s.io/v1",
    "kind": "CustomResourceDefinition",
    "metadata": {"name": "widgets.example.io"},
    "spec": {
        "group": "example.io",
        "names": {"kind": "Widget", "plural": "widgets"},
        "versions": [
            {
                "name": "v1",
                "served": True,
                "schema": {
                    "openAPIV3Schema": {
                        "type": "object",
                        "required": ["spec"],
                        "properties": {
                            "apiVersion": {"type": "string"},
                            "kind": {"type": "string"},
                            "metadata": {"type": "object"},
                            "spec": {
                                "type": "object",
                                "required": ["size"],
                                "properties": {
                                    "size": {"x-kubernetes-int-or-string": True},
                                    "labels": {"type": "object", "additionalProperties": {"type": "string"}},
                                    "free": {"type": "object", "x-kubernetes-preserve-unknown-fields": True},
                                },
                            },
                        },
                    }
                },
            },
            {"name": "v1alpha1", "served": False, "schema": {"openAPIV3Schema": {"type": "object"}}},
        ],
    },
}


def test_each_served_version_becomes_one_file_named_as_kubeconform_looks_it_up():
    """Kubeconform finds a custom resource at <group>/<kind>_<version>.json; a version not served is left out."""
    assert set(crd_json_schemas.json_schemas(CRD)) == {"example.io/widget_v1.json"}


def test_an_object_with_named_properties_refuses_any_other_key():
    """Strict like the Kubernetes schemas: a misspelt or misplaced key fails instead of passing unnoticed."""
    schema = crd_json_schemas.json_schemas(CRD)["example.io/widget_v1.json"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["spec"]["additionalProperties"] is False


def test_maps_and_free_objects_stay_open():
    """An object typed as a map, or one Kubernetes keeps unknown fields of, still takes any key."""
    spec = crd_json_schemas.json_schemas(CRD)["example.io/widget_v1.json"]["properties"]["spec"]
    assert spec["properties"]["labels"]["additionalProperties"] == {"type": "string"}
    assert "additionalProperties" not in spec["properties"]["free"]


def test_an_int_or_string_field_takes_either():
    """Kubernetes' int-or-string marker becomes a schema JSON Schema understands."""
    spec = crd_json_schemas.json_schemas(CRD)["example.io/widget_v1.json"]["properties"]["spec"]
    assert spec["properties"]["size"]["oneOf"] == [{"type": "string"}, {"type": "integer"}]


def test_required_fields_are_kept():
    """A resource missing a field its CRD requires fails, as the API server would refuse it."""
    schema = crd_json_schemas.json_schemas(CRD)["example.io/widget_v1.json"]
    assert schema["required"] == ["spec"]
    assert schema["properties"]["spec"]["required"] == ["size"]


def test_the_command_line_writes_every_crd_of_every_file(tmp_path: Path):
    """Each CustomResourceDefinition in the given files is written under the output folder; other kinds are skipped."""
    source = tmp_path / "crds.yaml"
    source.write_text(yaml.safe_dump_all([CRD, {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": "x"}}]))
    out = tmp_path / "out"
    assert crd_json_schemas.main([str(source), "--out", str(out)]) == 0
    written = json.loads((out / "example.io" / "widget_v1.json").read_text())
    assert written["properties"]["spec"]["required"] == ["size"]
    assert [path.relative_to(out).as_posix() for path in out.rglob("*.json")] == ["example.io/widget_v1.json"]
