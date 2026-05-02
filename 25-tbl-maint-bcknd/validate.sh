#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating table-maintenance backend (context: ${KUBE_CONTEXT})"

kubectl rollout status deployment/table-maintenance-backend \
  -n default --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Checking health endpoint..."
kubectl exec -n default \
  "$(kubectl get pod -l app=table-maintenance-backend -n default --context "${KUBE_CONTEXT}" -o jsonpath='{.items[0].metadata.name}')" \
  --context "${KUBE_CONTEXT}" \
  -- python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"

echo "==> Backend is ready."
