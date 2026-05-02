#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deploying PostgreSQL for table-maintenance (context: ${KUBE_CONTEXT})"

kubectl apply -f "$SCRIPT_DIR/postgres-pvc.yaml" --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/postgres-deployment.yaml" --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/postgres-service.yaml" --context "${KUBE_CONTEXT}"

echo "==> Done."
