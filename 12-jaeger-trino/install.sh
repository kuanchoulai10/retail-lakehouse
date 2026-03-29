#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing Jaeger for Trino (context: ${KUBE_CONTEXT})"

kubectl apply -f "$SCRIPT_DIR/jaeger.yaml" -n trino --context "${KUBE_CONTEXT}"

echo "==> Done."
