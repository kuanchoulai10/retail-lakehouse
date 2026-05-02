#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deploying table-maintenance scheduler (context: ${KUBE_CONTEXT})"

kubectl apply -f "$SCRIPT_DIR/scheduler-deployment.yaml" --context "${KUBE_CONTEXT}"

echo "==> Waiting for rollout..."
kubectl rollout status deployment/table-maintenance-scheduler \
  -n default --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Done."
