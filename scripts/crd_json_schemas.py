"""Turn CustomResourceDefinitions into the JSON schemas kubeconform reads.

kubeconform validates a custom resource against `<group>/<kind>_<version>.json` under a schema location.
Each served version of each CRD in the given files is written there, strict like kubeconform's own
Kubernetes schemas: an object with named properties refuses any other key, unless Kubernetes keeps its
unknown fields or it is typed as a map. `x-kubernetes-int-or-string` becomes a string-or-integer schema.

Usage: crd_json_schemas.py <crd.yaml>... --out <dir>
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import yaml

NESTED = ("properties", "patternProperties")
COMBINED = ("allOf", "anyOf", "oneOf")


def _strict(node: Any) -> Any:
    if not isinstance(node, dict):
        return node
    for key in NESTED:
        if key in node:
            node[key] = {name: _strict(child) for name, child in node[key].items()}
    for key in COMBINED:
        if key in node:
            node[key] = [_strict(child) for child in node[key]]
    if isinstance(node.get("items"), dict):
        node["items"] = _strict(node["items"])
    if isinstance(node.get("additionalProperties"), dict):
        node["additionalProperties"] = _strict(node["additionalProperties"])
    if node.pop("x-kubernetes-int-or-string", False):
        node["oneOf"] = [{"type": "string"}, {"type": "integer"}]
    if (
        "properties" in node
        and "additionalProperties" not in node
        and not node.get("x-kubernetes-preserve-unknown-fields")
    ):
        node["additionalProperties"] = False
    return node


def json_schemas(crd: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return each served version's schema of the CRD, keyed by the path kubeconform looks it up at."""
    group = crd["spec"]["group"]
    kind = crd["spec"]["names"]["kind"].lower()
    return {
        f"{group}/{kind}_{version['name']}.json": _strict(copy.deepcopy(version["schema"]["openAPIV3Schema"]))
        for version in crd["spec"]["versions"]
        if version.get("served", True)
    }


def main(argv: list[str] | None = None) -> int:
    """Write the schemas of every CRD in the given files under the output folder."""
    parser = argparse.ArgumentParser(description="Turn CRDs into the JSON schemas kubeconform reads.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    for source in args.files:
        for doc in yaml.safe_load_all(source.read_text()):
            if not doc or doc.get("kind") != "CustomResourceDefinition":
                continue
            for path, schema in json_schemas(doc).items():
                target = args.out / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
