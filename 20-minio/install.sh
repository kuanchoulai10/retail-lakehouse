#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deploying MinIO (context: ${KUBE_CONTEXT})"

kubectl create namespace minio --dry-run=client -o yaml | kubectl apply -f - --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/minio.yaml" --context "${KUBE_CONTEXT}"

echo "==> Done."
