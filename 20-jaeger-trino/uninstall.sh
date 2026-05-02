#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Uninstalling Jaeger for Trino (context: ${KUBE_CONTEXT})"

kubectl delete -f "$SCRIPT_DIR/jaeger.yaml" -n trino --context "${KUBE_CONTEXT}"

echo "==> Done."
