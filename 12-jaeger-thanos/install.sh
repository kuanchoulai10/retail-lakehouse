#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing Jaeger for Thanos (context: ${KUBE_CONTEXT})"

kubectl apply -f "$SCRIPT_DIR/jaeger.yaml" -n thanos --context "${KUBE_CONTEXT}"

echo "==> Done."
