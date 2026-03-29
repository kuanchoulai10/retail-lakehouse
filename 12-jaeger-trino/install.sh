#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Installing Jaeger for Trino (context: ${KUBE_CONTEXT})"

kubectl apply -f jaeger.yaml -n trino --context "${KUBE_CONTEXT}"

echo "==> Done."
