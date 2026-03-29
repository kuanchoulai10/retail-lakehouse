#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Installing Prometheus Operator (context: ${KUBE_CONTEXT})"

kubectl apply -k . --context "${KUBE_CONTEXT}"

echo "==> Done."
