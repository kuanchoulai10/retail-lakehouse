#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing Jaeger for Thanos (context: ${KUBE_CONTEXT})"

kubectl create namespace thanos --dry-run=client -o yaml | kubectl apply -f - --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/jaeger.yaml" -n thanos --context "${KUBE_CONTEXT}"

echo "==> Done."
