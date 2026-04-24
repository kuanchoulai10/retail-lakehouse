#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deploying table-maintenance backend (context: ${KUBE_CONTEXT})"

kubectl apply -f "$SCRIPT_DIR/backend-rbac.yaml" --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/backend-service.yaml" --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/backend-deployment.yaml" --context "${KUBE_CONTEXT}"

echo "==> Waiting for rollout..."
kubectl rollout status deployment/table-maintenance-backend \
  -n default --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Done."
