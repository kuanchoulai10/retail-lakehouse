#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating table-maintenance scheduler (context: ${KUBE_CONTEXT})"

kubectl rollout status deployment/table-maintenance-scheduler \
  -n default --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Checking scheduler logs for tick output..."
POD=$(kubectl get pod -l app=table-maintenance-scheduler -n default \
  --context "${KUBE_CONTEXT}" -o jsonpath='{.items[0].metadata.name}')
kubectl logs "$POD" -n default --context "${KUBE_CONTEXT}" --tail=5 | grep -q "Scheduler tick"

echo "==> Scheduler is ready."
