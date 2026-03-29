#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Installing Prometheus Operator (context: ${KUBE_CONTEXT})"

kubectl apply -k . --context "${KUBE_CONTEXT}"

echo "==> Done."
